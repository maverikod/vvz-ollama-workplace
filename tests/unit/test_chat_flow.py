"""Unit tests for chat_flow: no tool_calls, with tool_calls, proxy error in content."""

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
from ollama_workstation.chat_flow import run_chat_flow  # noqa: E402
from ollama_workstation.provider_client_config_generator import (  # noqa: E402
    generate_provider_clients_section,
)

_DEFAULT_POLICY = CommandsPolicyConfig(
    allowed_commands=(),
    forbidden_commands=(),
    commands_policy=COMMANDS_POLICY_DENY_BY_DEFAULT,
)


@pytest.fixture
def config() -> WorkstationConfig:
    provider_clients_data = generate_provider_clients_section(validate=False)
    return WorkstationConfig(
        mcp_proxy_url="http://localhost:3004",
        ollama_base_url="http://localhost:11434",
        ollama_model="llama3.1",
        commands_policy_config=_DEFAULT_POLICY,
        provider_clients_data=provider_clients_data,
    )


@pytest.mark.asyncio
async def test_chat_flow_requires_provider_clients_data_no_legacy_fallback() -> None:
    """run_chat_flow raises when provider_clients_data is None (no legacy resolver)."""
    config_no_pc = WorkstationConfig(
        mcp_proxy_url="http://localhost:3004",
        ollama_base_url="http://localhost:11434",
        ollama_model="llama3.1",
        commands_policy_config=_DEFAULT_POLICY,
        provider_clients_data=None,
    )
    with pytest.raises(ValueError, match="provider_clients_data is required"):
        await run_chat_flow(config_no_pc, [{"role": "user", "content": "Hi"}])


@pytest.mark.asyncio
async def test_chat_flow_no_tool_calls(config: WorkstationConfig) -> None:
    messages = [{"role": "user", "content": "Hello"}]
    mock_response = {
        "message": {"role": "assistant", "content": "Hi there."},
        "prompt_eval_count": None,
        "eval_count": None,
    }
    mock_provider_client = MagicMock()
    mock_provider_client.chat = MagicMock(return_value=mock_response)
    with (
        patch("ollama_workstation.chat_flow.is_model_ready", return_value=True),
        patch(
            "ollama_workstation.chat_flow.get_default_client",
            return_value=mock_provider_client,
        ),
    ):
        result = await run_chat_flow(config, messages)
    assert result.get("error") is None
    assert result.get("message") == "Hi there."
    assert len(result.get("history", [])) >= 2


@pytest.mark.asyncio
async def test_chat_flow_tool_call_appends_tool_msg(config: WorkstationConfig) -> None:
    messages = [{"role": "user", "content": "List servers"}]
    first_response = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"function": {"name": "list_servers", "arguments": "{}"}}],
        },
        "prompt_eval_count": None,
        "eval_count": None,
    }
    second_response = {
        "message": {"role": "assistant", "content": "Here are the servers."},
        "prompt_eval_count": None,
        "eval_count": None,
    }
    mock_provider_client = MagicMock()
    mock_provider_client.chat = MagicMock(side_effect=[first_response, second_response])
    with (
        patch("ollama_workstation.chat_flow.is_model_ready", return_value=True),
        patch(
            "ollama_workstation.chat_flow.get_default_client",
            return_value=mock_provider_client,
        ),
    ):
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
    mock_response = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"function": {"name": "list_servers", "arguments": "{}"}}],
        },
        "prompt_eval_count": None,
        "eval_count": None,
    }
    mock_provider_client = MagicMock()
    mock_provider_client.chat = MagicMock(return_value=mock_response)
    with (
        patch("ollama_workstation.chat_flow.is_model_ready", return_value=True),
        patch(
            "ollama_workstation.chat_flow.get_default_client",
            return_value=mock_provider_client,
        ),
    ):
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
