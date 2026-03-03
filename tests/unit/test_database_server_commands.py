"""
Unit tests for database_server adapter commands.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from unittest.mock import patch

import pytest

from mcp_proxy_adapter.commands.result import ErrorResult

from database_server.commands import COMMAND_CLASSES, register_database_commands
from database_server.commands.message_write_command import MessageWriteCommand
from database_server.commands.session_get_command import SessionGetCommand


def test_message_write_command_schema_strict() -> None:
    """message_write schema has required fields and additionalProperties false."""
    schema = MessageWriteCommand.get_schema()
    assert schema.get("type") == "object"
    assert schema.get("additionalProperties") is False
    assert "uuid" in (schema.get("required") or [])
    assert "created_at" in (schema.get("required") or [])
    assert "source" in (schema.get("required") or [])
    assert "body" in (schema.get("required") or [])
    assert "session_id" in (schema.get("required") or [])
    assert "properties" in schema
    assert schema["properties"].get("source", {}).get("enum") == [
        "user",
        "model",
        "tool",
        "external_agent",
    ]


def test_session_get_command_schema_strict() -> None:
    """session_get schema: session_id required, no extra props."""
    schema = SessionGetCommand.get_schema()
    assert schema.get("type") == "object"
    assert schema.get("additionalProperties") is False
    assert schema.get("required") == ["session_id"]


def test_register_database_commands_registers_all() -> None:
    """register_database_commands registers all command classes."""

    class MockRegistry:
        def __init__(self) -> None:
            self.registered: list = []

        def register(self, cmd_cls: type, category: str) -> None:
            self.registered.append((cmd_cls, category))

    reg = MockRegistry()
    register_database_commands(reg)
    assert len(reg.registered) == len(COMMAND_CLASSES)
    names = {c.name for c, _ in reg.registered}
    assert "message_write" in names
    assert "messages_get_by_session" in names
    assert "session_get" in names
    assert "session_create" in names
    assert "session_update" in names


@pytest.mark.asyncio
async def test_message_write_execute_returns_error_when_not_redis() -> None:
    """When storage backend is not redis, message_write returns ErrorResult."""
    with patch("database_server.commands.message_write_command._get_config") as m:
        m.return_value = {"database_server": {"storage": {"backend": "local"}}}
        cmd = MessageWriteCommand()
        result = await cmd.execute(
            uuid="u1",
            created_at="2025-01-01T00:00:00Z",
            source="user",
            body="hi",
            session_id="s1",
        )
    assert isinstance(result, ErrorResult)
    assert "redis" in (getattr(result, "message", str(result)).lower())
