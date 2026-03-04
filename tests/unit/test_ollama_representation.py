"""
Unit tests for OllamaRepresentation (step 08).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from ollama_workstation.command_schema import CommandSchema  # noqa: E402
from ollama_workstation.ollama_representation import (  # noqa: E402
    OllamaRepresentation,
    register_ollama_models,
)
from ollama_workstation.representation_registry import (  # noqa: E402
    RepresentationRegistry,
)


def test_serialize_tools_ollama_format() -> None:
    """serialize_tools produces type function, function name/description/parameters."""
    rep = OllamaRepresentation()
    tool_list = [
        ("my_tool", CommandSchema("echo", "Echo back", {"type": "object"})),
    ]
    out = rep.serialize_tools(tool_list)
    assert len(out) == 1
    assert out[0]["type"] == "function"
    assert out[0]["function"]["name"] == "my_tool"
    assert out[0]["function"]["description"] == "Echo back"
    assert out[0]["function"]["parameters"] == {"type": "object"}


def test_serialize_messages_role_content() -> None:
    """serialize_messages preserves role and content."""
    rep = OllamaRepresentation()
    messages = [{"role": "user", "content": "Hello"}]
    out = rep.serialize_messages(messages)
    assert out == [{"role": "user", "content": "Hello"}]


def test_format_tool_result() -> None:
    """format_tool_result: dict -> JSON string, other -> str."""
    rep = OllamaRepresentation()
    assert rep.format_tool_result({"a": 1}) == '{"a": 1}'
    assert rep.format_tool_result("ok") == "ok"
    assert rep.format_tool_result(42) == "42"


def test_register_ollama_models() -> None:
    """register_ollama_models registers representation for each model_id."""
    reg = RepresentationRegistry()
    register_ollama_models(reg, ["llama3.2", "qwen3"])
    assert reg.get_representation("llama3.2") is reg.get_representation("qwen3")
