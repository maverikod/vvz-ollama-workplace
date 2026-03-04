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
    """get_schema() has messages or (session_id + content); model/stream optional."""
    schema = OllamaChatCommand.get_schema()
    assert schema["type"] == "object"
    assert "messages" in schema["properties"]
    assert schema["properties"]["messages"]["type"] == "array"
    assert "session_id" in schema["properties"]
    assert "content" in schema["properties"]
    assert "model" in schema["properties"]
    assert "stream" in schema["properties"]
    assert "max_tool_rounds" in schema["properties"]
    assert isinstance(schema.get("required"), list)


def test_schema_has_description_and_examples() -> None:
    """Schema has root description and examples array (man-like)."""
    schema = OllamaChatCommand.get_schema()
    assert "description" in schema
    assert "examples" in schema
    assert len(schema["examples"]) >= 1


def test_get_metadata_returns_full_metadata() -> None:
    """get_metadata() returns name, description, params, result/error schema."""
    meta = OllamaChatCommand.get_metadata()
    assert meta["name"] == "ollama_chat"
    assert "description" in meta
    assert meta["params"] == OllamaChatCommand.get_schema()
    assert "result_schema" in meta
    assert "error_schema" in meta
    assert "error_codes" in meta
    assert len(meta["error_codes"]) >= 1
    assert "examples" in meta


@pytest.mark.asyncio
async def test_execute_returns_success_result_with_message_and_history() -> None:
    """execute() returns SuccessResult with data.message and data.history."""
    cmd = OllamaChatCommand()
    ready_state = {"status": "ready", "current_model": None, "message": None}
    with patch(
        "ollama_workstation.commands.ollama_chat_command.get_state",
        return_value=ready_state,
    ):
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
                result = await cmd.execute(messages=[{"role": "user", "content": "Hi"}])
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


@pytest.mark.asyncio
async def test_execute_session_mode_session_not_found() -> None:
    """When session_id + content given but session missing, return ErrorResult."""
    cmd = OllamaChatCommand()
    mock_store = MagicMock()
    mock_store.get.return_value = None
    ready_state = {"status": "ready", "current_model": None, "message": None}
    with patch(
        "ollama_workstation.commands.ollama_chat_command.get_state",
        return_value=ready_state,
    ):
        with patch(
            "ollama_workstation.commands.ollama_chat_command.load_config",
            return_value=MagicMock(
                mcp_proxy_url="http://p",
                ollama_base_url="http://o",
                ollama_model="m",
                ollama_timeout=60.0,
                max_tool_rounds=10,
                redis_host="localhost",
                redis_port=6379,
                redis_password=None,
                redis_key_prefix="message",
            ),
        ):
            with patch(
                "ollama_workstation.commands.ollama_chat_command._get_session_store",
                return_value=mock_store,
            ):
                result = await cmd.execute(
                    session_id="00000000-0000-0000-0000-000000000000",
                    content="Hello",
                )
    assert result.to_dict().get("success") is False
    assert "Session not found" in (result.message or "")


@pytest.mark.asyncio
async def test_execute_session_mode_uses_context_builder() -> None:
    """Session_id + content: context from ContextBuilder is passed to run_chat_flow."""
    from ollama_workstation.commands import ollama_chat_command as mod

    cmd = OllamaChatCommand()
    session_id = "11111111-1111-1111-1111-111111111111"
    content = "new user msg"
    serialized_from_builder = [{"role": "assistant", "content": "prior reply"}]
    mock_session = MagicMock()
    mock_session.model = "llama3.2"
    mock_store = MagicMock()
    mock_store.get.return_value = mock_session
    mock_redis = MagicMock()
    config = MagicMock(
        mcp_proxy_url="http://p",
        ollama_base_url="http://o",
        ollama_model="m",
        ollama_timeout=60.0,
        max_tool_rounds=10,
        redis_host="localhost",
        redis_port=6379,
        redis_password=None,
        redis_key_prefix="message",
        max_context_tokens=4096,
        last_n_messages=10,
        min_semantic_tokens=256,
        min_documentation_tokens=0,
        relevance_slot_mode="fixed_order",
        embedding_server_id="embedding-service",
        embedding_command="embed",
    )
    ready_state = {"status": "ready", "current_model": None, "message": None}
    with patch.object(mod, "get_state", return_value=ready_state):
        with patch.object(mod, "load_config", return_value=config):
            with patch.object(mod.redis, "Redis", return_value=mock_redis):
                run_chat_flow_mock = AsyncMock(
                    return_value={
                        "message": "ok",
                        "history": serialized_from_builder
                        + [
                            {"role": "user", "content": content},
                            {"role": "assistant", "content": "ok"},
                        ],
                    },
                )
                with patch(
                    "ollama_workstation.context_builder.ContextBuilder.build",
                    new_callable=AsyncMock,
                    return_value=(MagicMock(), serialized_from_builder),
                ):
                    with patch.object(mod, "run_chat_flow", run_chat_flow_mock):
                        with patch.object(
                            mod, "_get_session_store", return_value=mock_store
                        ):
                            result = await cmd.execute(
                                session_id=session_id,
                                content=content,
                            )
    assert result.to_dict().get("success") is True
    run_chat_flow_mock.assert_called_once()
    call_kw = run_chat_flow_mock.call_args[1]
    messages = call_kw.get("messages")
    assert messages is not None
    assert messages[0] == {"role": "assistant", "content": "prior reply"}
    assert messages[-1] == {"role": "user", "content": content}
