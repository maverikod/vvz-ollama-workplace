"""
Unit tests for context_file_loader (rules, standards, tools from disk).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from ollama_workstation.context_file_loader import (  # noqa: E402
    load_text_file,
    load_tools_json,
)


def test_load_text_file_empty_path_returns_none() -> None:
    """load_text_file with empty path returns None."""
    assert load_text_file(None) is None
    assert load_text_file("") is None
    assert load_text_file("   ") is None


def test_load_text_file_missing_returns_none() -> None:
    """load_text_file with non-existent path returns None."""
    assert load_text_file("/nonexistent/path/file.txt") is None


def test_load_text_file_reads_content(tmp_path: Path) -> None:
    """load_text_file returns stripped file content."""
    f = tmp_path / "rules.md"
    f.write_text("  Line one.\nLine two.  \n", encoding="utf-8")
    assert load_text_file(str(f)) == "Line one.\nLine two."


def test_load_tools_json_empty_path_returns_none() -> None:
    """load_tools_json with empty path returns None."""
    assert load_tools_json(None) is None
    assert load_tools_json("") is None


def test_load_tools_json_missing_returns_none() -> None:
    """load_tools_json with non-existent path returns None."""
    assert load_tools_json("/nonexistent/tools.json") is None


def test_load_tools_json_valid_returns_list(tmp_path: Path) -> None:
    """load_tools_json returns list of function tools."""
    tools = [
        {
            "type": "function",
            "function": {
                "name": "list_servers",
                "description": "List servers",
                "parameters": {"type": "object"},
            },
        },
    ]
    f = tmp_path / "tools.json"
    f.write_text(json.dumps(tools), encoding="utf-8")
    result = load_tools_json(str(f))
    assert result is not None
    assert len(result) == 1
    assert result[0]["function"]["name"] == "list_servers"


def test_load_tools_json_invalid_json_returns_none(tmp_path: Path) -> None:
    """load_tools_json with invalid JSON returns None."""
    f = tmp_path / "bad.json"
    f.write_text("not json", encoding="utf-8")
    assert load_tools_json(str(f)) is None


def test_load_tools_json_not_list_returns_none(tmp_path: Path) -> None:
    """load_tools_json when root is not a list returns None."""
    f = tmp_path / "obj.json"
    f.write_text('{"a": 1}', encoding="utf-8")
    assert load_tools_json(str(f)) is None
