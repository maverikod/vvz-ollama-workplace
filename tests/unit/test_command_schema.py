"""
Unit tests for CommandSchema (step 03).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from ollama_workstation.command_schema import CommandSchema  # noqa: E402


def test_schema_name_description_parameters() -> None:
    """CommandSchema has name, description, parameters."""
    s = CommandSchema(
        name="echo",
        description="Echo back",
        parameters={"type": "object", "properties": {}},
    )
    assert s.name == "echo"
    assert s.description == "Echo back"
    assert s.parameters == {"type": "object", "properties": {}}


def test_parameters_must_be_dict() -> None:
    """parameters must be a dict (JSON Schema)."""
    with pytest.raises(ValueError, match="parameters must be a dict"):
        CommandSchema(name="x", description="y", parameters=[])  # type: ignore[arg-type]
