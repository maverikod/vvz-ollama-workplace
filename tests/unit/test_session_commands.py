"""
Unit tests for session adapter commands (step 13).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from ollama_workstation.commands import (  # noqa: E402
    AddCommandToSessionCommand,
    RemoveCommandFromSessionCommand,
    SessionInitCommand,
    SessionUpdateCommand,
)
from ollama_workstation.session_store import InMemorySessionStore  # noqa: E402


def _make_store():
    return InMemorySessionStore()


def test_session_init_schema() -> None:
    """SessionInitCommand.get_schema() has optional model and lists."""
    schema = SessionInitCommand.get_schema()
    assert schema["type"] == "object"
    assert "model" in schema["properties"]
    assert "allowed_commands" in schema["properties"]
    assert "forbidden_commands" in schema["properties"]
    assert schema["required"] == []


def test_session_init_metadata() -> None:
    """SessionInitCommand.get_metadata() has name session_init."""
    meta = SessionInitCommand.get_metadata()
    assert meta["name"] == "session_init"
    assert "session_id" in str(meta["result_schema"])


@pytest.mark.asyncio
async def test_session_init_execute_returns_session_id() -> None:
    """SessionInitCommand.execute() returns SuccessResult with session_id."""
    cmd = SessionInitCommand()
    with patch(
        "ollama_workstation.commands.session_init_command._get_session_store"
    ) as get_store:
        store = _make_store()
        get_store.return_value = store
        result = await cmd.execute(parameters={"model": "llama3.2"})
    assert result.to_dict().get("success") is True
    assert "session_id" in result.data
    assert len(result.data["session_id"]) > 0


def test_session_update_schema() -> None:
    """SessionUpdateCommand.get_schema() requires session_id."""
    schema = SessionUpdateCommand.get_schema()
    assert schema["required"] == ["session_id"]
    assert "model" in schema["properties"]


@pytest.mark.asyncio
async def test_session_update_execute_success() -> None:
    """SessionUpdateCommand.execute() updates session and returns ok."""
    cmd = SessionUpdateCommand()
    with patch(
        "ollama_workstation.commands.session_update_command._get_session_store"
    ) as get_store:
        store = _make_store()
        s = store.create({"model": "x"})
        get_store.return_value = store
        result = await cmd.execute(
            parameters={"session_id": s.id, "model": "llama3.2"}
        )
    assert result.to_dict().get("success") is True
    assert result.data.get("ok") is True
    assert store.get(s.id).model == "llama3.2"


@pytest.mark.asyncio
async def test_session_update_missing_session_id() -> None:
    """SessionUpdateCommand.execute() without session_id returns error."""
    cmd = SessionUpdateCommand()
    result = await cmd.execute(parameters={})
    assert result.to_dict().get("success") is False
    assert "session_id" in (result.message or "").lower()


def test_add_command_to_session_schema() -> None:
    """AddCommandToSession schema requires session_id and command_id."""
    schema = AddCommandToSessionCommand.get_schema()
    assert set(schema["required"]) == {"session_id", "command_id"}


@pytest.mark.asyncio
async def test_add_command_to_session_success() -> None:
    """AddCommandToSessionCommand.execute() adds command to session."""
    cmd = AddCommandToSessionCommand()
    patch_get = (
        "ollama_workstation.commands.add_command_to_session_command."
        "_get_session_store"
    )
    with patch(patch_get) as get_store:
        store = _make_store()
        s = store.create({})
        get_store.return_value = store
        result = await cmd.execute(
            parameters={"session_id": s.id, "command_id": "echo.proxy"},
            config_path=None,
        )
    assert result.to_dict().get("success") is True
    assert result.data.get("ok") is True
    updated = store.get(s.id)
    assert "echo.proxy" in updated.allowed_commands


@pytest.mark.asyncio
async def test_add_command_forbidden_by_config_rejected() -> None:
    """AddCommandToSession rejects command in config forbidden list."""
    cmd = AddCommandToSessionCommand()
    patch_load = (
        "ollama_workstation.commands.add_command_to_session_command."
        "load_config"
    )
    patch_get = (
        "ollama_workstation.commands.add_command_to_session_command."
        "_get_session_store"
    )
    with patch(patch_load) as load_config_mock:
        config = MagicMock()
        config.commands_policy_config = MagicMock()
        config.commands_policy_config.forbidden_commands = ("forbidden.cmd",)
        load_config_mock.return_value = config
        with patch(patch_get) as get_store:
            store = _make_store()
            s = store.create({})
            get_store.return_value = store
            result = await cmd.execute(
                parameters={"session_id": s.id, "command_id": "forbidden.cmd"},
                config_path="/some/config.json",
            )
    assert result.to_dict().get("success") is False
    assert "forbidden" in (result.message or "").lower()
    assert "forbidden.cmd" not in store.get(s.id).allowed_commands


def test_remove_command_from_session_schema() -> None:
    """RemoveCommandFromSessionCommand.get_schema() requires both ids."""
    schema = RemoveCommandFromSessionCommand.get_schema()
    assert set(schema["required"]) == {"session_id", "command_id"}


@pytest.mark.asyncio
async def test_remove_command_from_session_success() -> None:
    """RemoveCommandFromSessionCommand removes command from allowed."""
    cmd = RemoveCommandFromSessionCommand()
    patch_get = (
        "ollama_workstation.commands.remove_command_from_session_command."
        "_get_session_store"
    )
    with patch(patch_get) as get_store:
        store = _make_store()
        s = store.create({"allowed_commands": ["echo.proxy"]})
        get_store.return_value = store
        result = await cmd.execute(
            parameters={"session_id": s.id, "command_id": "echo.proxy"}
        )
    assert result.to_dict().get("success") is True
    updated = store.get(s.id)
    assert "echo.proxy" not in updated.allowed_commands
    assert "echo.proxy" in updated.forbidden_commands
