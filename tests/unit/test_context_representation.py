"""
Unit tests for ContextRepresentation ABC (step 07).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from ollama_workstation.context_representation import ContextRepresentation  # noqa: E402


class StubRepresentation(ContextRepresentation):
    """Minimal concrete for tests."""

    def serialize_tools(self, tool_list: list) -> list:
        """Return empty list."""
        return []

    def serialize_messages(self, messages: list) -> list:
        """Return messages as-is."""
        return list(messages)


def test_stub_serialize_tools() -> None:
    """Stub returns empty list for tools."""
    r = StubRepresentation()
    assert r.serialize_tools([("a", None)]) == []


def test_stub_serialize_messages() -> None:
    """Stub returns messages as-is."""
    r = StubRepresentation()
    assert r.serialize_messages([{"role": "user", "content": "hi"}]) == [
        {"role": "user", "content": "hi"},
    ]


def test_max_context_tokens_default_none() -> None:
    """Base default max_context_tokens returns None."""
    r = StubRepresentation()
    assert r.max_context_tokens() is None
