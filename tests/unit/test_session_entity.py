"""
Unit tests for Session entity (step 05).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from ollama_workstation.session_entity import Session  # noqa: E402


def test_create_generates_uuid() -> None:
    """Session.create() generates UUID4 id when session_id not given."""
    s = Session.create(model="llama3.2")
    assert s.id
    assert len(s.id) == 36
    assert s.model == "llama3.2"
    assert s.allowed_commands == ()
    assert s.forbidden_commands == ()


def test_create_with_session_id() -> None:
    """Session.create(session_id=X) uses given id."""
    s = Session.create(session_id="my-id", model="qwen3")
    assert s.id == "my-id"
    assert s.model == "qwen3"


def test_session_empty_id_raises() -> None:
    """Session with empty id raises in __post_init__."""
    with pytest.raises(ValueError, match="id is required"):
        Session(
            id="",
            model="m",
            allowed_commands=(),
            forbidden_commands=(),
        )
