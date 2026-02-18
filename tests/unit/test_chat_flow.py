"""Unit tests for chat_flow: no tool_calls, with tool_calls, proxy error in content."""

from unittest.mock import AsyncMock, MagicMock, patch
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))  # noqa: E402
from ollama_workstation.config import WorkstationConfig  # noqa: E402
from ollama_workstation.chat_flow import run_chat_flow  # noqa: E402


@pytest.fixture
def config() -> WorkstationConfig:
    return WorkstationConfig(
        mcp_proxy_url="http://localhost:3004",
        ollama_base_url="http://localhost:11434",
        ollama_model="llama3.1",
    )


@pytest.mark.asyncio
async def test_chat_flow_no_tool_calls(config: WorkstationConfig) -> None:
    messages = [{"role": "user", "content": "Hello"}]
    mock_response = {"message": {"role": "assistant", "content": "Hi there."}}
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value=mock_response)
        mock_post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__.return_value.post = mock_post
        result = await run_chat_flow(config, messages)
    assert result.get("error") is None
    assert result.get("message") == "Hi there."
    assert len(result.get("history", [])) >= 2


@pytest.mark.asyncio
async def test_chat_flow_tool_call_appends_tool_msg(config: WorkstationConfig) -> None:
    messages = [{"role": "user", "content": "List servers"}]
    call_count = 0

    def post(_url: str, json: dict = None, **kwargs: object) -> object:
        nonlocal call_count
        call_count += 1
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        if call_count == 1:
            resp.json = MagicMock(return_value={
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"function": {"name": "list_servers", "arguments": "{}"}}
                    ],
                },
            })
        else:
            resp.json = MagicMock(return_value={
                "message": {
                    "role": "assistant",
                    "content": "Here are the servers.",
                },
            })
        return resp

    with patch("httpx.AsyncClient") as mock_client_cls:
        ctx = mock_client_cls.return_value.__aenter__.return_value
        ctx.post = AsyncMock(side_effect=post)
        with patch("ollama_workstation.chat_flow.ProxyClient") as mock_proxy_cls:
            mock_proxy = AsyncMock()
            mock_proxy.list_servers = AsyncMock(return_value={"servers": []})
            mock_proxy.close = AsyncMock()
            mock_proxy_cls.return_value = mock_proxy
            result = await run_chat_flow(config, messages)
    assert result.get("error") is None
    assert "history" in result
    roles = [m.get("role") for m in result["history"]]
    assert "tool" in roles


@pytest.mark.asyncio
async def test_chat_flow_proxy_error_in_tool_content(config: WorkstationConfig) -> None:
    from ollama_workstation.proxy_client import ProxyClientError
    messages = [{"role": "user", "content": "List servers"}]
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(
            return_value={
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"function": {"name": "list_servers", "arguments": "{}"}}
                    ],
                },
            }
        )
        ctx = mock_client_cls.return_value.__aenter__.return_value
        ctx.post = AsyncMock(return_value=mock_resp)
        with patch("ollama_workstation.chat_flow.ProxyClient") as mock_pc:
            mock_proxy = AsyncMock()
            mock_proxy.list_servers = AsyncMock(
                side_effect=ProxyClientError("Proxy down")
            )
            mock_proxy.close = AsyncMock()
            mock_pc.return_value = mock_proxy
            result = await run_chat_flow(config, messages)
    assert "history" in result
    tool_msgs = [m for m in result["history"] if m.get("role") == "tool"]
    assert len(tool_msgs) >= 1
    content = (tool_msgs[0].get("content") or "").lower()
    assert "proxy down" in content or "error" in content
