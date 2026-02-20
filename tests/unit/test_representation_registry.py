"""
Unit tests for RepresentationRegistry (step 07).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from ollama_workstation.context_representation import ContextRepresentation  # noqa: E402
from ollama_workstation.representation_registry import RepresentationRegistry  # noqa: E402


class StubRep(ContextRepresentation):
    def serialize_tools(self, tool_list):  # noqa: ANN001
        return []

    def serialize_messages(self, messages):  # noqa: ANN001
        return list(messages)


def test_register_and_get() -> None:
    """register then get_representation returns same instance."""
    reg = RepresentationRegistry()
    rep = StubRep()
    reg.register("llama3.2", rep)
    assert reg.get_representation("llama3.2") is rep


def test_unknown_model_raises_without_default() -> None:
    """get_representation(unknown) raises KeyError when no default."""
    reg = RepresentationRegistry()
    with pytest.raises(KeyError, match="No representation"):
        reg.get_representation("unknown")


def test_unknown_model_returns_default() -> None:
    """get_representation(unknown) returns default when set."""
    default = StubRep()
    reg = RepresentationRegistry(default=default)
    assert reg.get_representation("unknown") is default
