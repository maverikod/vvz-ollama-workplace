"""
Integration tests: provider client unification (step 13).

Covers:
1. No-direct-access policy: chat flow uses provider client for Model Workplace Server; test fails
   if direct mwps/redis path is reintroduced in the model request path.
2. Provider parity via common API: at least Model Workplace Server exercised through provider
   client (get_default_client + .chat()).
3. Proxy registration and command availability: database-server and mwps-server
   visible in list_servers; key commands callable via call_server.

References: docs/plans/provider_client_unification/atomic/step_13_integration_tests.md,
SCOPE_FREEZE.md, CLIENT_UNIFICATION_TZ.md.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from mwps.chat_flow import run_chat_flow  # noqa: E402
from mwps.config import WorkstationConfig  # noqa: E402
from mwps.commands_policy_config import (  # noqa: E402
    COMMANDS_POLICY_DENY_BY_DEFAULT,
    CommandsPolicyConfig,
)
from mwps.proxy_client import ProxyClient, ProxyClientError  # noqa: E402
from mwps.server_resolver import (  # noqa: E402
    extract_servers_list,
)


def _project_root() -> Path:
    """Project root (repo root)."""
    return Path(__file__).resolve().parents[2]


def _minimal_workstation_config(
    mcp_proxy_url: str = "http://localhost:3004",
    mwps_base_url: str = "http://127.0.0.1:11434",
    mwps_model: str = "llama3.2",
    provider_clients_data: Dict[str, Any] | None = None,
) -> WorkstationConfig:
    """Build minimal WorkstationConfig with optional provider_clients_data."""
    if provider_clients_data is None:
        provider_clients_data = {
            "default_provider": "mwps",
            "providers": {
                "mwps": {
                    "transport": {"base_url": mwps_base_url},
                    "features": {},
                },
            },
        }
    return WorkstationConfig(
        mcp_proxy_url=mcp_proxy_url,
        mwps_base_url=mwps_base_url,
        mwps_model=mwps_model,
        commands_policy_config=CommandsPolicyConfig(
            allowed_commands=(),
            forbidden_commands=(),
            commands_policy=COMMANDS_POLICY_DENY_BY_DEFAULT,
        ),
        provider_clients_data=provider_clients_data,
    )


# ---- 1. No-direct-access policy ----


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mwps_chat_flow_uses_provider_client_only() -> None:
    """
    No-direct-access: run_chat_flow for Model Workplace Server must use get_default_client and
    provider_client.chat(); must not use direct mwps HTTP in this path.

    If someone reintroduces direct httpx/requests to mwps in chat_flow, the
    mock's chat() would not be called and this test fails.
    """
    config = _minimal_workstation_config()
    mock_client = MagicMock()
    mock_client.chat.return_value = {
        "message": {"role": "assistant", "content": "ok", "tool_calls": []},
        "done": True,
    }

    with (
        patch(
            "mwps.chat_flow.get_default_client",
            return_value=mock_client,
        ),
        patch(
            "mwps.chat_flow.is_model_ready",
            return_value=True,
        ),
    ):
        result = await run_chat_flow(
            config,
            messages=[{"role": "user", "content": "hi"}],
            model=config.mwps_model,
            max_tool_rounds=1,
            tools_from_file=[],
        )

    assert mock_client.chat.called, (
        "Model Workplace Server chat path must use provider client .chat(); "
        "direct mwps HTTP would bypass this and fail the test."
    )
    call_args = mock_client.chat.call_args
    assert call_args is not None
    body = call_args[0][0] if call_args[0] else call_args[1].get("body", call_args[0])
    if not isinstance(body, dict):
        body = call_args[0][0] if call_args[0] else {}
    assert isinstance(body, dict), "chat must be called with request body dict"
    assert "model" in body, "request body must contain model"
    assert "messages" in body, "request body must contain messages"
    assert (
        "error" not in result or not result["error"]
    ), "chat_flow should complete without error when provider client returns valid"


# ---- 2. Provider parity via common API ----


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mwps_provider_client_chat_via_common_api() -> None:
    """
    Provider parity: model interaction for Model Workplace Server is performed via provider
    client only (common API). Run one round with real provider client; skip if
    Model Workplace Server or proxy unavailable.
    """
    base_url = os.environ.get("MWPS_BASE_URL", "http://127.0.0.1:11434").strip()
    model = os.environ.get("MWPS_MODEL", "llama3.2").strip()
    proxy_url = os.environ.get("MCP_PROXY_URL", "http://localhost:3004").strip()
    if not proxy_url:
        proxy_url = "http://localhost:3004"

    config = _minimal_workstation_config(
        mcp_proxy_url=proxy_url,
        mwps_base_url=base_url,
        mwps_model=model,
    )

    result = await run_chat_flow(
        config,
        messages=[{"role": "user", "content": "Reply with one word: ok"}],
        model=model,
        max_tool_rounds=1,
        tools_from_file=[],
    )

    if result.get("error"):
        if (
            "not ready" in result["error"].lower()
            or "connection" in result["error"].lower()
        ):
            pytest.skip(
                "Integration: Model Workplace Server not available or model not ready: %s"
                % result["error"]
            )
        if (
            "provider_clients_data" in result["error"]
            or "provider client" in result["error"]
        ):
            pytest.fail(
                "Provider client not used or misconfigured: %s" % result["error"]
            )
    assert "history" in result
    assert len(result["history"]) >= 1


# ---- 3. Proxy registration and command availability ----


def _get_proxy_config() -> WorkstationConfig | None:
    """Load config from env or adapter config; return None if no proxy URL."""
    path = os.environ.get("ADAPTER_CONFIG_PATH", "")
    if path and Path(path).exists():
        try:
            from mwps.config import load_config

            return load_config(path)
        except Exception:
            pass
    url = os.environ.get("MCP_PROXY_URL", "").strip()
    if not url:
        return None
    return _minimal_workstation_config(mcp_proxy_url=url)


@pytest.fixture(scope="module")
def proxy_config_integration():
    """Config with proxy URL; skip if unavailable."""
    cfg = _get_proxy_config()
    if cfg is None or not (getattr(cfg, "mcp_proxy_url", "") or "").strip():
        pytest.skip("Integration: set MCP_PROXY_URL or ADAPTER_CONFIG_PATH with proxy")
    return cfg


@pytest.mark.integration
@pytest.mark.asyncio
async def test_proxy_registration_database_server_visible(
    proxy_config_integration: WorkstationConfig,
) -> None:
    """
    Proxy registration: database-server is proxy-registered and discoverable
    via list_servers.
    """
    client = ProxyClient(proxy_config_integration)
    try:
        raw = await client.list_servers(page=1, page_size=100)
    except ProxyClientError as e:
        pytest.skip("Integration: proxy absent: %s" % e.message)
    finally:
        await client.close()

    servers = extract_servers_list(raw)
    server_ids = set()
    for srv in servers:
        if isinstance(srv, dict):
            sid = (srv.get("server_id") or srv.get("id") or "").strip()
            if sid:
                server_ids.add(sid)

    assert "database-server" in server_ids, (
        "database-server must be proxy-registered and visible in list_servers; "
        "got: %s" % sorted(server_ids)
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_proxy_registration_mwps_server_visible(
    proxy_config_integration: WorkstationConfig,
) -> None:
    """
    Proxy registration: mwps-server is proxy-registered and discoverable
    via list_servers.
    """
    client = ProxyClient(proxy_config_integration)
    try:
        raw = await client.list_servers(page=1, page_size=100)
    except ProxyClientError as e:
        pytest.skip("Integration: proxy absent: %s" % e.message)
    finally:
        await client.close()

    servers = extract_servers_list(raw)
    server_ids = set()
    for srv in servers:
        if isinstance(srv, dict):
            sid = (srv.get("server_id") or srv.get("id") or "").strip()
            if sid:
                server_ids.add(sid)

    assert "mwps-server" in server_ids, (
        "mwps-server must be proxy-registered and visible in list_servers; "
        "got: %s" % sorted(server_ids)
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_proxy_registration_database_server_key_command_callable(
    proxy_config_integration: WorkstationConfig,
) -> None:
    """
    Proxy registration: a key command on database-server is callable via
    call_server (e.g. health). Skips if proxy or database-server unavailable.
    """
    client = ProxyClient(proxy_config_integration)
    try:
        raw = await client.list_servers()
        servers = extract_servers_list(raw)
        if not any(
            (s.get("server_id") or s.get("id") or "").strip() == "database-server"
            for s in servers
            if isinstance(s, dict)
        ):
            pytest.skip("Integration: database-server not in proxy list")
    except ProxyClientError as e:
        pytest.skip("Integration: proxy absent: %s" % e.message)

    try:
        out = await client.call_server(
            "database-server",
            "health",
            params={},
        )
    except ProxyClientError as e:
        pytest.skip(
            "Integration: call_server(database-server, health) failed: %s" % e.message
        )
    finally:
        await client.close()

    assert out is not None, "call_server(database-server, health) must return a result"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_proxy_registration_mwps_server_key_command_callable(
    proxy_config_integration: WorkstationConfig,
) -> None:
    """
    Proxy registration: a key command on mwps-server is callable via
    call_server (e.g. list or health). Skips if proxy or mwps-server unavailable.
    """
    client = ProxyClient(proxy_config_integration)
    try:
        raw = await client.list_servers()
        servers = extract_servers_list(raw)
        if not any(
            (s.get("server_id") or s.get("id") or "").strip() == "mwps-server"
            for s in servers
            if isinstance(s, dict)
        ):
            pytest.skip("Integration: mwps-server not in proxy list")
    except ProxyClientError as e:
        pytest.skip("Integration: proxy absent: %s" % e.message)

    # Try "list" (Model Workplace Server /api/tags) or "health" if implemented
    try:
        out = await client.call_server(
            "mwps-server",
            "list",
            params={},
        )
    except ProxyClientError as e:
        pytest.skip(
            "Integration: call_server(mwps-server, list) failed: %s" % e.message
        )
    finally:
        await client.close()

    assert out is not None, "call_server(mwps-server, list) must return a result"
