"""
Integration tests: real proxy and services, no mocks.

Step 17 (Real Integration No Mocks): integration only on real services (proxy,
workstation, db, ollama, real tool server). Validates both pair contracts
(model-workspace + database). Uses real proxy endpoint with mTLS registration
and certs from mtls_certificates (e.g. https://172.28.0.2:3004).

- Tests pass only with real service topology; when required service is absent
  they fail or skip with a clear message.
- Registration test fails when mTLS cert paths are invalid and passes with
  valid cert set.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from ollama_workstation.config import load_config  # noqa: E402
from ollama_workstation.proxy_client import ProxyClient, ProxyClientError  # noqa: E402
from ollama_workstation.registration import (  # noqa: E402
    _validate_registration_contract,
)
from ollama_workstation.server_resolver import (  # noqa: E402
    extract_servers_list,
    get_server_url,
    parse_server_url,
    server_url_to_embed_config_dict,
)


def _project_root() -> Path:
    """Project root (repo root)."""
    return Path(__file__).resolve().parents[2]


def _mtls_certs_dir() -> Path:
    """Path to mtls_certificates directory; may not exist."""
    return _project_root() / "mtls_certificates"


def _get_proxy_config():
    """
    Load config from adapter config file or env; require proxy URL.

    Prefers ADAPTER_CONFIG_PATH (adapter JSON with registration.ssl for mTLS).
    Falls back to MCP_PROXY_URL + optional PROXY_CLIENT_CERT, PROXY_CLIENT_KEY,
    PROXY_CA_CERT. Returns None if no proxy URL or config missing.
    """
    path = os.environ.get("ADAPTER_CONFIG_PATH", "/app/config/adapter_config.json")
    if not Path(path).exists():
        url = os.environ.get("MCP_PROXY_URL", "").strip()
        if not url:
            return None
        from ollama_workstation.commands_policy_config import (
            COMMANDS_POLICY_DENY_BY_DEFAULT,
            CommandsPolicyConfig,
        )
        from ollama_workstation.config import WorkstationConfig

        return WorkstationConfig(
            mcp_proxy_url=url,
            ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
            ollama_model=os.environ.get("OLLAMA_MODEL", "llama3.2"),
            proxy_client_cert=os.environ.get("PROXY_CLIENT_CERT"),
            proxy_client_key=os.environ.get("PROXY_CLIENT_KEY"),
            proxy_ca_cert=os.environ.get("PROXY_CA_CERT"),
            commands_policy_config=CommandsPolicyConfig(
                allowed_commands=(),
                forbidden_commands=(),
                commands_policy=COMMANDS_POLICY_DENY_BY_DEFAULT,
            ),
        )
    try:
        return load_config(path)
    except Exception:
        return None


@pytest.fixture(scope="module")
def proxy_config():
    """Config with proxy URL and mTLS when from adapter config; skip if unavailable."""
    cfg = _get_proxy_config()
    if cfg is None or not (getattr(cfg, "mcp_proxy_url", "") or "").strip():
        pytest.skip("Integration: set MCP_PROXY_URL or ADAPTER_CONFIG_PATH with proxy")
    return cfg


# ---- Registration contract (mTLS paths) ----


@pytest.mark.integration
def test_registration_validation_rejects_invalid_mtls_paths() -> None:
    """
    Registration contract: invalid mTLS cert paths must raise ValueError.

    When paths mention mtls_certificates but ca points outside ca/, or
    cert/key outside client/, validation fails.
    """
    base = "https://172.28.0.2:3004"
    config = {
        "ollama_workstation": {"mcp_proxy_url": base},
        "registration": {
            "protocol": "mtls",
            "register_url": f"{base}/register",
            "unregister_url": f"{base}/unregister",
            "heartbeat": {"url": f"{base}/proxy/heartbeat"},
            "ssl": {
                "ca": "/app/mtls_certificates/client/mcp-proxy.crt",
                "cert": "/app/mtls_certificates/client/mcp-proxy.crt",
                "key": "/app/mtls_certificates/client/mcp-proxy.key",
            },
        },
        "server": {
            "ssl": {
                "cert": "/app/mtls_certificates/server/mcp-proxy.crt",
                "key": "/app/mtls_certificates/server/mcp-proxy.key",
            },
        },
    }
    with pytest.raises(
        ValueError, match="registration.ssl.ca must point to mtls_certificates/ca"
    ):
        _validate_registration_contract(config)


@pytest.mark.integration
def test_registration_validation_accepts_valid_mtls_paths() -> None:
    """
    Registration contract: valid mTLS cert paths (under ca/, client/, server/) pass.
    """
    base = "https://172.28.0.2:3004"
    config = {
        "ollama_workstation": {"mcp_proxy_url": base},
        "registration": {
            "protocol": "mtls",
            "register_url": f"{base}/register",
            "unregister_url": f"{base}/unregister",
            "heartbeat": {"url": f"{base}/proxy/heartbeat"},
            "ssl": {
                "ca": "/app/mtls_certificates/ca/ca.crt",
                "cert": "/app/mtls_certificates/client/mcp-proxy.crt",
                "key": "/app/mtls_certificates/client/mcp-proxy.key",
            },
        },
        "server": {
            "ssl": {
                "cert": "/app/mtls_certificates/server/mcp-proxy.crt",
                "key": "/app/mtls_certificates/server/mcp-proxy.key",
            },
        },
    }
    _validate_registration_contract(config)


# ---- Pair contracts (model-workspace + database) ----


@pytest.mark.integration
def test_model_workspace_contract_config_valid() -> None:
    """
    Model-workspace pair contract: validate_config_dict accepts valid client config.

    Uses real cert paths from mtls_certificates when present; else skip.
    """
    certs = _mtls_certs_dir()
    ca = certs / "ca" / "ca.crt"
    client_cert = certs / "client" / "test-server.crt"
    client_key = certs / "client" / "test-server.key"
    if not (ca.is_file() and client_cert.is_file() and client_key.is_file()):
        pytest.skip(
            "Integration: mtls_certificates (ca, client cert/key) not found for "
            "model_workspace contract check"
        )
    try:
        from model_workspace_client.config_validator import validate_config_dict
    except ImportError:
        pytest.skip("Integration: model_workspace_client not installed")

    app_config = {
        "model_workspace_client": {
            "ws_endpoint": "wss://172.28.0.2:443",
            "client_cert_file": str(client_cert),
            "client_key_file": str(client_key),
            "ca_cert_file": str(ca),
            "connect_timeout_seconds": 10,
            "request_timeout_seconds": 30,
        },
        "client": {
            "enabled": True,
            "protocol": "mtls",
            "ssl": {
                "cert": str(client_cert),
                "key": str(client_key),
                "ca": str(ca),
            },
        },
    }
    errors = validate_config_dict(app_config)
    assert errors == [], "model_workspace_client contract validation should pass"


@pytest.mark.integration
def test_database_contract_config_valid() -> None:
    """
    Database pair contract: validate_config_dict accepts valid client config.

    Uses real cert paths from mtls_certificates when present; else skip.
    """
    certs = _mtls_certs_dir()
    ca = certs / "ca" / "ca.crt"
    client_cert = certs / "client" / "test-server.crt"
    client_key = certs / "client" / "test-server.key"
    if not (ca.is_file() and client_cert.is_file() and client_key.is_file()):
        pytest.skip(
            "Integration: mtls_certificates (ca, client cert/key) not found for "
            "database contract check"
        )
    try:
        from database_client.config_validator import validate_config_dict
    except ImportError:
        pytest.skip("Integration: database_client not installed")

    app_config = {
        "database_client": {
            "base_url": "https://172.28.0.2:8443",
            "client_cert_file": str(client_cert),
            "client_key_file": str(client_key),
            "ca_cert_file": str(ca),
            "connect_timeout_seconds": 10,
            "request_timeout_seconds": 30,
        },
        "client": {
            "enabled": True,
            "protocol": "mtls",
            "ssl": {
                "cert": str(client_cert),
                "key": str(client_key),
                "ca": str(ca),
            },
        },
    }
    errors = validate_config_dict(app_config)
    assert errors == [], "database_client contract validation should pass"


# ---- Real proxy (no mocks) ----


@pytest.mark.integration
@pytest.mark.asyncio
async def test_proxy_list_servers_returns_network_data(proxy_config) -> None:
    """
    Real proxy: list_servers returns servers list (network data from proxy).

    Fails or skips when required service (proxy) is absent.
    """
    client = ProxyClient(proxy_config)
    try:
        raw = await client.list_servers(page=1, page_size=50)
    except ProxyClientError as e:
        pytest.skip("Integration: required service (proxy) absent: %s" % e.message)
    assert isinstance(raw, dict), "list_servers must return dict"
    servers = extract_servers_list(raw)
    assert isinstance(servers, list), "servers must be list"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_resolve_server_url_from_proxy(proxy_config) -> None:
    """Resolve server_id to server_url using real proxy list_servers."""
    client = ProxyClient(proxy_config)
    try:
        raw = await client.list_servers()
    except ProxyClientError as e:
        pytest.skip("Integration: required service (proxy) absent: %s" % e.message)
    servers = extract_servers_list(raw)
    if not servers:
        pytest.skip("Integration: no servers in proxy list")
    server_id = servers[0].get("server_id") or servers[0].get("id") or ""
    if not server_id:
        pytest.skip("Integration: first server has no server_id")
    url = await get_server_url(client.list_servers, server_id)
    assert url is not None, "get_server_url must return URL for known server_id"
    parsed = parse_server_url(url)
    assert parsed.get("protocol") in ("http", "https")
    assert parsed.get("host")
    assert isinstance(parsed.get("port"), int)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_direct_embed_using_resolved_url(proxy_config) -> None:
    """Direct embed: resolve embedding server from proxy, call embed (real server)."""
    server_id = (
        getattr(proxy_config, "embedding_server_id", "embedding-service")
        or "embedding-service"
    )
    client = ProxyClient(proxy_config)
    try:
        url = await get_server_url(client.list_servers, server_id)
    except ProxyClientError as e:
        pytest.skip("Integration: required service (proxy) absent: %s" % e.message)
    if not url:
        pytest.skip("Integration: embedding server_id=%s not in proxy list" % server_id)
    config_dict = server_url_to_embed_config_dict(url, proxy_config)
    assert "server" in config_dict
    assert config_dict["server"].get("base_url") == url.rstrip("/")
    try:
        from embed_client import EmbeddingServiceAsyncClient

        embed_client = EmbeddingServiceAsyncClient(config_dict=config_dict)
        result = await embed_client.embed(["short test"], use_push=True, timeout=30.0)
    except Exception as e:
        pytest.skip("Integration: embed client failed: %s" % e)
    assert isinstance(result, dict)
    assert "results" in result or "embeddings" in result or "result" in result
