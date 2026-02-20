"""
Unit tests for ContextBuilder, TrimmedContext, RelevanceSlotBuilder (step 10).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from ollama_workstation.context_builder import (  # noqa: E402
    ContextBuilder,
    ContextBuilderError,
)
from ollama_workstation.message_store import MessageStore  # noqa: E402
from ollama_workstation.representation_registry import (  # noqa: E402
    RepresentationRegistry,
)
from ollama_workstation.session_store import InMemorySessionStore  # noqa: E402


class StubMessageStore(MessageStore):
    """Returns fixed list for get_messages."""

    def __init__(self, messages: list) -> None:
        self._messages = messages

    def get_messages(self, session_id: str) -> list:
        return list(self._messages)


def test_build_session_not_found_raises() -> None:
    """build() with unknown session_id raises ContextBuilderError."""
    session_store = InMemorySessionStore()
    reg = RepresentationRegistry()
    msg_store = StubMessageStore([])
    builder = ContextBuilder(session_store, reg, msg_store)
    with pytest.raises(ContextBuilderError, match="Session not found"):
        builder.build(
            "no-such-id",
            {},
            4096,
            last_n_messages=10,
            min_semantic_tokens=256,
        )


def test_build_model_not_set_raises() -> None:
    """build() when session.model is None raises ContextBuilderError."""
    session_store = InMemorySessionStore()
    session_store.create({"id": "s1", "model": None})
    reg = RepresentationRegistry()
    msg_store = StubMessageStore([])
    builder = ContextBuilder(session_store, reg, msg_store)
    with pytest.raises(ContextBuilderError, match="model not set"):
        builder.build("s1", {}, 4096, last_n_messages=10, min_semantic_tokens=256)


def test_build_returns_trimmed_and_serialized() -> None:
    """build() with valid session returns TrimmedContext and serialized messages."""
    session_store = InMemorySessionStore()
    session_store.create({"id": "s1", "model": "llama3.2"})
    reg = RepresentationRegistry()
    from ollama_workstation.ollama_representation import OllamaRepresentation

    reg.register("llama3.2", OllamaRepresentation())
    msg_store = StubMessageStore(
        [
            {"source": "user", "body": "Hi", "created_at": "2025-01-01T00:00:00Z"},
        ]
    )
    builder = ContextBuilder(session_store, reg, msg_store)
    trimmed, serialized = builder.build(
        "s1", {}, 4096, last_n_messages=10, min_semantic_tokens=256
    )
    assert trimmed.last_n_messages == [{"role": "user", "content": "Hi"}]
    assert len(serialized) >= 1


def test_build_includes_standards_and_session_rules() -> None:
    """build() includes session.standards and session.session_rules in TrimmedContext."""
    session_store = InMemorySessionStore()
    session_store.create(
        {
            "id": "s1",
            "model": "llama3.2",
            "standards": ["Standard A", "Standard B"],
            "session_rules": ["Rule one", "Rule two"],
        }
    )
    reg = RepresentationRegistry()
    from ollama_workstation.ollama_representation import OllamaRepresentation

    reg.register("llama3.2", OllamaRepresentation())
    msg_store = StubMessageStore([])
    builder = ContextBuilder(session_store, reg, msg_store)
    trimmed, serialized = builder.build(
        "s1", {}, 4096, last_n_messages=10, min_semantic_tokens=256
    )
    assert trimmed.standards == [
        {"role": "system", "content": "Standard A"},
        {"role": "system", "content": "Standard B"},
    ]
    assert trimmed.session_rules == [
        {"role": "system", "content": "Rule one"},
        {"role": "system", "content": "Rule two"},
    ]
    # Order: standards -> session_rules -> last_n_messages -> relevance_slot
    assert serialized[0]["content"] == "Standard A"
    assert serialized[1]["content"] == "Standard B"
    assert serialized[2]["content"] == "Rule one"
    assert serialized[3]["content"] == "Rule two"
