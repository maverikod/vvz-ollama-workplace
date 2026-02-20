"""
Unit tests for SessionStore and InMemorySessionStore (step 05).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from ollama_workstation.session_entity import Session  # noqa: E402
from ollama_workstation.session_store import InMemorySessionStore  # noqa: E402


def test_create_and_get() -> None:
    """create() returns session; get() returns it by id."""
    store = InMemorySessionStore()
    s = store.create({"model": "llama3.2", "allowed_commands": ["a.b"]})
    assert s.id
    assert s.model == "llama3.2"
    assert s.allowed_commands == ("a.b",)
    got = store.get(s.id)
    assert got is not None
    assert got.id == s.id
    assert got.model == s.model


def test_get_missing_returns_none() -> None:
    """get(unknown_id) returns None."""
    store = InMemorySessionStore()
    assert store.get("no-such-id") is None


def test_update_model() -> None:
    """update(session_id, {model: X}) changes model."""
    store = InMemorySessionStore()
    s = store.create({"model": "llama3.2"})
    updated = store.update(s.id, {"model": "qwen3"})
    assert updated.model == "qwen3"
    assert store.get(s.id).model == "qwen3"


def test_update_missing_raises() -> None:
    """update(unknown_id) raises KeyError."""
    store = InMemorySessionStore()
    with pytest.raises(KeyError, match="Session not found"):
        store.update("no-such-id", {"model": "x"})
