"""Unit tests for tools.py: three tools, OLLAMA format, tech spec params."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))  # noqa: E402
from ollama_workstation.tools import get_ollama_tools  # noqa: E402


def test_tools_count() -> None:
    tools = get_ollama_tools()
    assert len(tools) == 3


def test_tool_names() -> None:
    tools = get_ollama_tools()
    names = [t["function"]["name"] for t in tools]
    assert set(names) == {"list_servers", "call_server", "help"}


def test_each_tool_has_required_fields() -> None:
    for t in get_ollama_tools():
        assert t["type"] == "function"
        fn = t["function"]
        assert "name" in fn and "description" in fn and "parameters" in fn
        assert fn["parameters"].get("type") == "object"
        assert "properties" in fn["parameters"]


def test_list_servers_parameters() -> None:
    tools = get_ollama_tools()
    ls = next(t for t in tools if t["function"]["name"] == "list_servers")
    props = ls["function"]["parameters"]["properties"]
    assert "page" in props and "page_size" in props and "filter_enabled" in props


def test_call_server_parameters() -> None:
    tools = get_ollama_tools()
    cs = next(t for t in tools if t["function"]["name"] == "call_server")
    props = cs["function"]["parameters"]["properties"]
    assert "server_id" in props and "copy_number" in props
    assert "command" in props and "params" in props
    req = cs["function"]["parameters"]["required"]
    assert "server_id" in req and "command" in req


def test_help_parameters() -> None:
    tools = get_ollama_tools()
    hp = next(t for t in tools if t["function"]["name"] == "help")
    props = hp["function"]["parameters"]["properties"]
    assert "server_id" in props and "copy_number" in props and "command" in props
    assert "server_id" in hp["function"]["parameters"]["required"]
