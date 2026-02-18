"""
Unit tests for OllamaChatCommand: schema shape, execute result structure.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from unittest.mock import AsyncMock, MagicMock, patch
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))  # noqa: E402
from ollama_workstation.commands import OllamaChatCommand  # noqa: E402


def test_schema_has_messages_required() -> None:
    """get_schema() has messages required, model/stream/max_tool_rounds optional."""
    schema = OllamaChatCommand.get_schema()
    assert schema["type"] == "object"
    assert "messages" in schema["required"]
    assert "messages" in schema["properties"]
    assert schema["properties"]["messages"]["type"] == "array"
    assert "model" in schema["properties"]
    assert "stream" in schema["properties"]
    assert "max_tool_rounds" in schema["properties"]


def test_schema_has_description_and_examples() -> None:
    """Schema has root description and examples array (man-like)."""
    schema = OllamaChatCommand.get_schema()
    assert "description" in schema
    assert "examples" in schema
    assert len(schema["examples"]) >= 1


@pytest.mark.asyncio
async def test_execute_returns_success_result_with_message_and_history() -> None:
    """execute() returns SuccessResult with data.message and data.history."""
    cmd = OllamaChatCommand()
    with patch(
        "ollama_workstation.commands.ollama_chat_command.load_config"
    ) as load_cfg:
        with patch(
            "ollama_workstation.commands.ollama_chat_command.run_chat_flow",
            new_callable=AsyncMock,
            return_value={
                "message": "Done.",
                "history": [
                    {"role": "user", "content": "Hi"},
                    {"role": "assistant", "content": "Done."},
                ],
            },
        ):
            load_cfg.return_value = MagicMock(
                mcp_proxy_url="http://p",
                ollama_base_url="http://o",
                ollama_model="m",
                ollama_timeout=60.0,
                max_tool_rounds=10,
            )
            result = await cmd.execute(
                messages=[{"role": "user", "content": "Hi"}]
            )
    assert result.to_dict().get("success") is True
    assert result.data.get("message") == "Done."
    assert "history" in result.data


@pytest.mark.asyncio
async def test_execute_config_error_returns_error_result() -> None:
    """When load_config raises ValueError, execute returns ErrorResult."""
    cmd = OllamaChatCommand()
    with patch(
        "ollama_workstation.commands.ollama_chat_command.load_config",
        side_effect=ValueError("mcp_proxy_url is required"),
    ):
        result = await cmd.execute(messages=[{"role": "user", "content": "Hi"}])
    assert result.to_dict().get("success") is False
    assert "mcp_proxy_url" in (result.message or getattr(result, "error", "") or "")
