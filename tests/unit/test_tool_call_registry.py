"""
Unit tests for ToolCallRegistry (step 02): register and resolve.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from ollama_workstation.tool_call_registry import ToolCallRegistry  # noqa: E402


def test_register_and_resolve() -> None:
    """Register display_name -> (command_name, server_id); resolve returns it."""
    reg = ToolCallRegistry()
    reg.register("ollama_chat_ollama_adapter", "ollama_chat", "ollama-adapter")
    assert reg.resolve("ollama_chat_ollama_adapter") == (
        "ollama_chat",
        "ollama-adapter",
    )


def test_unknown_name_raises_key_error() -> None:
    """Resolving unregistered name raises KeyError."""
    reg = ToolCallRegistry()
    reg.register("a_b", "a", "b")
    with pytest.raises(KeyError, match="Unknown tool name"):
        reg.resolve("unknown_tool")


def test_contains() -> None:
    """__contains__ returns True only for registered names."""
    reg = ToolCallRegistry()
    reg.register("x_y", "x", "y")
    assert "x_y" in reg
    assert "a_b" not in reg


def test_empty_display_name_raises() -> None:
    """Registering empty display_name raises ValueError."""
    reg = ToolCallRegistry()
    with pytest.raises(ValueError, match="non-empty"):
        reg.register("", "cmd", "srv")
