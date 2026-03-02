"""Unit tests for proxy_client: list_servers, call_server, help with mocked client."""

from unittest.mock import AsyncMock, MagicMock, patch
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))  # noqa: E402
from ollama_workstation.commands_policy_config import (  # noqa: E402
    COMMANDS_POLICY_DENY_BY_DEFAULT,
    CommandsPolicyConfig,
)
from ollama_workstation.config import WorkstationConfig  # noqa: E402
from ollama_workstation.proxy_client import (  # noqa: E402
    WS_CONTRACT_VERSION,
    config_to_adapter_params,
    ProxyClient,
    ProxyClientError,
)

_DEFAULT_POLICY = CommandsPolicyConfig(
    allowed_commands=(),
    forbidden_commands=(),
    commands_policy=COMMANDS_POLICY_DENY_BY_DEFAULT,
)


@pytest.fixture
def config() -> WorkstationConfig:
    return WorkstationConfig(
        mcp_proxy_url="http://localhost:3004",
        ollama_base_url="http://localhost:11434",
        ollama_model="llama3.1",
        commands_policy_config=_DEFAULT_POLICY,
    )


@pytest.mark.asyncio
async def test_list_servers_calls_proxy(config: WorkstationConfig) -> None:
    """list_servers uses JSON-RPC when REST /list and /servers are not available."""
    client = ProxyClient(config)
    client._client = AsyncMock()
    client._client.jsonrpc_call = AsyncMock(return_value={"result": {"servers": []}})
    client._client._extract_result = MagicMock(return_value={"servers": []})
    with patch.object(
        client, "_list_servers_rest", new_callable=AsyncMock, return_value=None
    ):
        out = await client.list_servers(page=1, page_size=10)
    assert out == {"servers": []}
    client._client.jsonrpc_call.assert_called_once_with(
        "list_servers", {"page": 1, "page_size": 10}
    )


@pytest.mark.asyncio
async def test_list_servers_rest_first(config: WorkstationConfig) -> None:
    """REST /list returns 200 -> list_servers returns it without JSON-RPC."""
    client = ProxyClient(config)
    rest_data = {"servers": [{"server_id": "s1", "server_url": "https://s1/"}]}
    with patch.object(
        client, "_list_servers_rest", new_callable=AsyncMock, return_value=rest_data
    ):
        out = await client.list_servers()
    assert out == rest_data


@pytest.mark.asyncio
async def test_call_server_calls_proxy(config: WorkstationConfig) -> None:
    client = ProxyClient(config)
    client._client = AsyncMock()
    client._client.jsonrpc_call = AsyncMock(return_value={"result": {"ok": True}})
    client._client._extract_result = MagicMock(return_value={"ok": True})
    out = await client.call_server("srv1", "echo", copy_number=1, params={"x": 1})
    assert out == {"ok": True}
    call_args = {
        "server_id": "srv1",
        "command": "echo",
        "copy_number": 1,
        "params": {"x": 1},
    }
    client._client.jsonrpc_call.assert_called_once_with("call_server", call_args)


@pytest.mark.asyncio
async def test_help_calls_proxy(config: WorkstationConfig) -> None:
    client = ProxyClient(config)
    client._client = AsyncMock()
    client._client.jsonrpc_call = AsyncMock(return_value={"result": {"usage": "..."}})
    client._client._extract_result = MagicMock(return_value={"usage": "..."})
    out = await client.help("srv1", command="echo")
    assert out == {"usage": "..."}
    client._client.jsonrpc_call.assert_called_once_with(
        "help", {"server_id": "srv1", "command": "echo"}
    )


@pytest.mark.asyncio
async def test_proxy_error_raises_proxy_client_error(config: WorkstationConfig) -> None:
    client = ProxyClient(config)
    client._client = AsyncMock()
    client._client.jsonrpc_call = AsyncMock(
        side_effect=RuntimeError("Connection refused")
    )
    with patch.object(
        client, "_list_servers_rest", new_callable=AsyncMock, return_value=None
    ):
        with pytest.raises(ProxyClientError, match="Connection refused"):
            await client.list_servers()


def test_ws_contract_version_constant() -> None:
    """WS contract identifier matches NAMING_FREEZE.md (ws-contract-v1)."""
    assert WS_CONTRACT_VERSION == "ws-contract-v1"


def test_config_to_adapter_params_wss_url() -> None:
    """wss:// URL yields protocol https and default port 443 for adapter ws_url."""
    cfg = WorkstationConfig(
        mcp_proxy_url="wss://proxy.example.com",
        ollama_base_url="http://localhost:11434",
        ollama_model="qwen",
        commands_policy_config=_DEFAULT_POLICY,
    )
    params = config_to_adapter_params(cfg)
    assert params["protocol"] == "https"
    assert params["host"] == "proxy.example.com"
    assert params["port"] == 443


def test_config_to_adapter_params_ws_url() -> None:
    """ws:// URL yields protocol http; explicit port in URL is preserved."""
    cfg = WorkstationConfig(
        mcp_proxy_url="ws://localhost:3004",
        ollama_base_url="http://localhost:11434",
        ollama_model="qwen",
        commands_policy_config=_DEFAULT_POLICY,
    )
    params = config_to_adapter_params(cfg)
    assert params["protocol"] == "http"
    assert params["port"] == 3004


def test_use_ws_first_true_for_wss() -> None:
    """_use_ws_first is True when mcp_proxy_url starts with wss://."""
    cfg = WorkstationConfig(
        mcp_proxy_url="wss://proxy:3004",
        ollama_base_url="http://localhost:11434",
        ollama_model="qwen",
        commands_policy_config=_DEFAULT_POLICY,
    )
    client = ProxyClient(cfg)
    assert client._use_ws_first() is True


def test_use_ws_first_false_for_https() -> None:
    """_use_ws_first is False for https:// (no WS-first)."""
    cfg = WorkstationConfig(
        mcp_proxy_url="https://proxy:3004",
        ollama_base_url="http://localhost:11434",
        ollama_model="qwen",
        commands_policy_config=_DEFAULT_POLICY,
    )
    client = ProxyClient(cfg)
    assert client._use_ws_first() is False


@pytest.mark.asyncio
async def test_ws_first_fallback_to_http_on_ws_failure() -> None:
    """When wss:// and _call_ws raises, fall back to _call_http and return result."""
    cfg = WorkstationConfig(
        mcp_proxy_url="wss://proxy:3004",
        ollama_base_url="http://localhost:11434",
        ollama_model="qwen",
        commands_policy_config=_DEFAULT_POLICY,
    )
    client = ProxyClient(cfg)
    client._client = AsyncMock()
    client._client.jsonrpc_call = AsyncMock(return_value={"result": {"servers": []}})
    client._client._extract_result = MagicMock(return_value={"servers": []})
    mock_ws = AsyncMock(side_effect=ConnectionError("ws fail"))
    with patch.object(client, "_call_ws", mock_ws):
        with patch.object(
            client, "_list_servers_rest", new_callable=AsyncMock, return_value=None
        ):
            out = await client.list_servers()
    assert out == {"servers": []}
    mock_ws.assert_called_once()
    client._client.jsonrpc_call.assert_called_once()


@pytest.mark.asyncio
async def test_http_url_uses_http_only_no_ws_attempt() -> None:
    """When URL is http://, _call uses only HTTP (no _call_ws)."""
    cfg = WorkstationConfig(
        mcp_proxy_url="http://localhost:3004",
        ollama_base_url="http://localhost:11434",
        ollama_model="qwen",
        commands_policy_config=_DEFAULT_POLICY,
    )
    client = ProxyClient(cfg)
    client._client = AsyncMock()
    client._client.jsonrpc_call = AsyncMock(return_value={"result": {"x": 1}})
    client._client._extract_result = MagicMock(return_value={"x": 1})
    with patch.object(client, "_call_ws", new_callable=AsyncMock) as mock_ws:
        out = await client.call_server("srv", "echo", params={})
    mock_ws.assert_not_called()
    assert out == {"x": 1}
