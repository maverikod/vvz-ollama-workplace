"""
Unit tests for ServerStatusCommand and model_loading_state.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from ollama_workstation.commands import ServerStatusCommand
from ollama_workstation.model_loading_state import (
    get_state,
    set_loading,
    set_ready,
)


def test_get_state_ready_by_default() -> None:
    """After set_ready (or default), get_state returns status ready."""
    set_ready()
    state = get_state()
    assert state["status"] == "ready"
    assert state.get("current_model") is None


def test_get_state_loading_after_set_loading() -> None:
    """After set_loading, get_state returns status loading_models."""
    set_loading("llama3.2", "Loading model llama3.2...")
    try:
        state = get_state()
        assert state["status"] == "loading_models"
        assert state["current_model"] == "llama3.2"
        assert "llama3.2" in (state.get("message") or "")
    finally:
        set_ready()


def test_server_status_command_schema_no_params() -> None:
    """server_status has no required params."""
    schema = ServerStatusCommand.get_schema()
    assert schema.get("required") == []
    assert schema.get("properties") == {}


@pytest.mark.asyncio
async def test_server_status_command_returns_state() -> None:
    """execute() returns SuccessResult with get_state() data."""
    set_ready()
    cmd = ServerStatusCommand()
    result = await cmd.execute()
    assert result.to_dict().get("success") is True
    assert "status" in result.data
    assert result.data["status"] in ("ready", "loading_models")
