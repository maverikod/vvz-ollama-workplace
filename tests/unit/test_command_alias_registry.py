"""
Unit tests for CommandAliasRegistry (step 04).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from ollama_workstation.command_alias_registry import CommandAliasRegistry  # noqa: E402


def test_no_alias_returns_none() -> None:
    """When no alias configured, get_display_name returns None (use safe name)."""
    reg = CommandAliasRegistry()
    assert reg.get_display_name("echo.ollama-adapter", "llama3.2") is None


def test_alias_configured_returns_display_name() -> None:
    """When alias is set, get_display_name returns it."""
    reg = CommandAliasRegistry({
        ("echo.ollama-adapter", "llama3.2"): "tool_echo",
    })
    assert reg.get_display_name("echo.ollama-adapter", "llama3.2") == "tool_echo"


def test_set_alias() -> None:
    """set_alias then get_display_name returns the name."""
    reg = CommandAliasRegistry()
    reg.set_alias("cmd.srv", "model1", "my_cmd")
    assert reg.get_display_name("cmd.srv", "model1") == "my_cmd"


def test_different_model_no_alias() -> None:
    """Alias for one model does not apply to another."""
    reg = CommandAliasRegistry({
        ("echo.ollama-adapter", "llama3.2"): "tool_echo",
    })
    assert reg.get_display_name("echo.ollama-adapter", "qwen3") is None
