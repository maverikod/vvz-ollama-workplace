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
