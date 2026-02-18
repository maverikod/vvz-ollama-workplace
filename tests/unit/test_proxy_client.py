"""Unit tests for proxy_client: list_servers, call_server, help with mocked client."""

from unittest.mock import AsyncMock, MagicMock
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))  # noqa: E402
from ollama_workstation.config import WorkstationConfig  # noqa: E402
from ollama_workstation.proxy_client import (  # noqa: E402
    ProxyClient,
    ProxyClientError,
)


@pytest.fixture
def config() -> WorkstationConfig:
    return WorkstationConfig(
        mcp_proxy_url="http://localhost:3004",
        ollama_base_url="http://localhost:11434",
        ollama_model="llama3.1",
    )


@pytest.mark.asyncio
async def test_list_servers_calls_proxy(config: WorkstationConfig) -> None:
    client = ProxyClient(config)
    client._client = AsyncMock()
    client._client.jsonrpc_call = AsyncMock(return_value={"result": {"servers": []}})
    client._client._extract_result = MagicMock(return_value={"servers": []})
    out = await client.list_servers(page=1, page_size=10)
    assert out == {"servers": []}
    client._client.jsonrpc_call.assert_called_once_with(
        "list_servers", {"page": 1, "page_size": 10}
    )


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
    with pytest.raises(ProxyClientError, match="Connection refused"):
        await client.list_servers()
