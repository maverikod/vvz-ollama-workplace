"""
Unit tests for docker_config_validation: ollama_workstation.ollama_models.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from ollama_workstation.docker_config_validation import (  # noqa: E402
    validate_project_config,
)


def test_ollama_models_valid_list() -> None:
    """Valid ollama_models (list of non-empty strings) adds no errors."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": {"ollama_models": ["llama3.2", "qwen3"]},
    }
    assert validate_project_config(app_config) == []


def test_ollama_models_empty_list() -> None:
    """Empty list is valid."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": {"ollama_models": []},
    }
    assert validate_project_config(app_config) == []


def test_ollama_models_missing_key() -> None:
    """Missing ollama_models key is valid (optional)."""
    app_config = {"server": {"protocol": "http"}, "ollama_workstation": {}}
    assert validate_project_config(app_config) == []


def test_ollama_models_not_list() -> None:
    """ollama_models must be a list."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": {"ollama_models": "llama3.2"},
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "must be a list" in errors[0]


def test_ollama_models_element_not_string() -> None:
    """Each element must be a string."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": {"ollama_models": ["llama3.2", 123]},
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "ollama_models[1]" in errors[0]
    assert "non-empty string" in errors[0]


def test_ollama_models_empty_string_element() -> None:
    """Empty string element is invalid."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": {"ollama_models": ["llama3.2", ""]},
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "ollama_models[1]" in errors[0]


def test_ollama_models_whitespace_only_invalid() -> None:
    """Whitespace-only element is invalid."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": {"ollama_models": ["  "]},
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "ollama_models[0]" in errors[0]


def test_commands_policy_valid() -> None:
    """Valid commands_policy and lists add no errors (step 01)."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": {
            "commands_policy": "allow_by_default",
            "allowed_commands": ["a.b"],
            "forbidden_commands": [],
        },
    }
    assert validate_project_config(app_config) == []


def test_commands_policy_invalid_value() -> None:
    """commands_policy must be allow_by_default or deny_by_default."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": {"commands_policy": "allow_all"},
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "commands_policy" in errors[0]
    assert "allow_by_default" in errors[0]


def test_allowed_commands_must_be_list() -> None:
    """allowed_commands must be a list."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": {"allowed_commands": "a.b"},
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "allowed_commands" in errors[0]
    assert "list" in errors[0]


def test_forbidden_commands_element_must_be_string() -> None:
    """forbidden_commands elements must be strings."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": {"forbidden_commands": ["a.b", 123]},
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "forbidden_commands[1]" in errors[0]
