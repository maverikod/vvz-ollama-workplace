"""
Unit tests for SessionStore, InMemorySessionStore, RedisSessionStore (step 05).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import json
import sys
from pathlib import Path
from typing import Dict

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from ollama_workstation.session_store import (  # noqa: E402
    InMemorySessionStore,
    RedisSessionStore,
)


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


class _MockRedis:
    """In-memory Redis-like client for testing RedisSessionStore."""

    def __init__(self) -> None:
        self._data: Dict[str, Dict[str, str]] = {}

    def hgetall(self, key: str) -> Dict[str, str]:
        return dict(self._data.get(key, {}))

    def hset(self, key: str, mapping: Dict[str, str]) -> None:
        if key not in self._data:
            self._data[key] = {}
        self._data[key].update(mapping)


def test_redis_store_create_and_get_with_standards_rules() -> None:
    """RedisSessionStore persists and returns session with standards and session_rules."""
    mock = _MockRedis()
    store = RedisSessionStore(mock, key_prefix="session")
    s = store.create(
        {
            "model": "llama3.2",
            "standards": ["Standard A", "Standard B"],
            "session_rules": ["Rule one"],
        }
    )
    assert s.id
    assert s.model == "llama3.2"
    assert s.standards == ("Standard A", "Standard B")
    assert s.session_rules == ("Rule one",)
    got = store.get(s.id)
    assert got is not None
    assert got.standards == s.standards
    assert got.session_rules == s.session_rules
    key = "session:" + s.id
    raw = mock._data.get(key, {})
    assert "standards" in raw
    assert json.loads(raw["standards"]) == ["Standard A", "Standard B"]
    assert json.loads(raw["session_rules"]) == ["Rule one"]


def test_redis_store_update_standards_rules() -> None:
    """RedisSessionStore.update can update standards and session_rules."""
    mock = _MockRedis()
    store = RedisSessionStore(mock, key_prefix="session")
    s = store.create({"model": "m", "standards": ["Old"], "session_rules": ["Old R"]})
    updated = store.update(s.id, {"standards": ["New A", "New B"], "session_rules": []})
    assert updated.standards == ("New A", "New B")
    assert updated.session_rules == ()
    got = store.get(s.id)
    assert got is not None
    assert got.standards == ("New A", "New B")
    assert got.session_rules == ()
