"""
Unit tests for ServerStatusCommand and model_loading_state.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from ollama_workstation.commands import (  # noqa: E402
    GetModelStateCommand,
    ServerStatusCommand,
    SetDefaultModelCommand,
)
from ollama_workstation.model_loading_state import (  # noqa: E402
    get_active_model,
    get_state,
    set_active_model,
    set_loading,
    set_model_ready,
    set_ready,
)


def test_get_state_ready_by_default() -> None:
    """When not loading and model ready, get_state returns status ready."""
    set_ready()
    set_model_ready(True)
    try:
        state = get_state()
        assert state["status"] == "ready"
        assert state.get("current_model") is None
        assert "active_model" in state
    finally:
        set_model_ready(False)


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


def test_set_active_model_get_active_model() -> None:
    """set_active_model/get_active_model hot-swap; None resets."""
    try:
        assert get_active_model() is None
        set_active_model("qwen2.5-coder:1.5b")
        assert get_active_model() == "qwen2.5-coder:1.5b"
        set_active_model("")
        assert get_active_model() is None
        set_active_model(None)
        assert get_active_model() is None
    finally:
        set_active_model(None)


@pytest.mark.asyncio
async def test_server_status_command_returns_state() -> None:
    """execute() returns SuccessResult with get_state() data."""
    set_ready()
    set_model_ready(True)
    try:
        cmd = ServerStatusCommand()
        result = await cmd.execute()
        assert result.to_dict().get("success") is True
        assert "status" in result.data
        assert result.data["status"] in ("ready", "loading_models")
        assert "active_model" in result.data
    finally:
        set_model_ready(False)


@pytest.mark.asyncio
async def test_get_model_state_command() -> None:
    """get_model_state returns status and model (same data as get_state)."""
    set_ready()
    set_model_ready(True)
    try:
        cmd = GetModelStateCommand()
        result = await cmd.execute()
        assert result.to_dict().get("success") is True
        assert result.data["status"] == "ready"
        assert "active_model" in result.data
        assert "current_model" in result.data
    finally:
        set_model_ready(False)


@pytest.mark.asyncio
async def test_set_default_model_command() -> None:
    """set_default_model sets active_model; empty resets."""
    try:
        set_active_model(None)
        cmd = SetDefaultModelCommand()
        result = await cmd.execute(model="llama3.2")
        assert result.to_dict().get("success") is True
        assert result.data.get("ok") is True
        assert result.data.get("active_model") == "llama3.2"
        result2 = await cmd.execute(model="")
        assert result2.data.get("active_model") is None
    finally:
        set_active_model(None)
