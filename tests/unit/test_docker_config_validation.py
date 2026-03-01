"""
Unit tests for docker_config_validation: ollama_workstation.ollama_models.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from ollama_workstation.docker_config_validation import (  # noqa: E402
    get_required_api_key_for_model,
    validate_commercial_model_keys,
    validate_project_config,
)


def _ow_base() -> dict:
    """Minimal ollama_workstation with required ollama_base_url or model_server_url."""
    return {"ollama_base_url": "http://localhost:11434"}


def test_ollama_models_valid_list() -> None:
    """Valid ollama_models (list of non-empty strings) adds no errors."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": {**_ow_base(), "ollama_models": ["llama3.2", "qwen3"]},
    }
    assert validate_project_config(app_config) == []


def test_ollama_models_empty_list() -> None:
    """Empty list is valid."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": {**_ow_base(), "ollama_models": []},
    }
    assert validate_project_config(app_config) == []


def test_ollama_models_missing_key() -> None:
    """Missing ollama_models key is valid (optional)."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": _ow_base(),
    }
    assert validate_project_config(app_config) == []


def test_model_server_url_or_ollama_base_required() -> None:
    """ollama_workstation must have ollama_base_url or model_server_url."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": {"ollama_models": []},
    }
    errors = validate_project_config(app_config)
    assert len(errors) >= 1
    assert "ollama_base_url" in errors[0] or "model_server_url" in errors[0]


def test_commercial_api_keys_must_be_non_empty_when_set() -> None:
    """When set, google_api_key / anthropic_api_key / openai_api_key must be non-empty."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": {
            **_ow_base(),
            "google_api_key": "",
        },
    }
    errors = validate_project_config(app_config)
    assert any("google_api_key" in e and "non-empty" in e for e in errors)


def test_get_required_api_key_for_model() -> None:
    """Commercial model ids map to required config key; local models return None."""
    assert get_required_api_key_for_model("gemini-1.5-flash") == "google_api_key"
    assert get_required_api_key_for_model("Gemini-2.0") == "google_api_key"
    assert get_required_api_key_for_model("claude-3-opus") == "anthropic_api_key"
    assert get_required_api_key_for_model("gpt-4o") == "openai_api_key"
    assert get_required_api_key_for_model("gpt-3.5-turbo") == "openai_api_key"
    assert get_required_api_key_for_model("o1-mini") == "openai_api_key"
    assert get_required_api_key_for_model("grok-2") == "xai_api_key"
    assert get_required_api_key_for_model("deepseek-chat") == "deepseek_api_key"
    assert get_required_api_key_for_model("llama3.2") is None
    assert get_required_api_key_for_model("qwen2.5-coder:1.5b") is None
    assert get_required_api_key_for_model("") is None


def test_validate_commercial_model_keys_missing_key() -> None:
    """Commercial model without corresponding API key yields error."""
    ow = _ow_base()
    errors = validate_commercial_model_keys(ow, "gemini-1.5-flash", [])
    assert len(errors) == 1
    assert "google_api_key" in errors[0]


def test_validate_commercial_model_keys_with_key_ok() -> None:
    """Commercial model with corresponding API key set passes."""
    ow = {**_ow_base(), "google_api_key": "sk-fake"}
    errors = validate_commercial_model_keys(ow, "gemini-1.5-flash", [])
    assert errors == []


def test_validate_commercial_model_keys_ollama_no_key_ok() -> None:
    """Ollama/local model does not require commercial key."""
    ow = _ow_base()
    errors = validate_commercial_model_keys(ow, "llama3.2", ["qwen2.5-coder:1.5b"])
    assert errors == []


def test_validate_project_config_commercial_model_requires_key() -> None:
    """Full validation: config with gemini as ollama_model and no google_api_key fails."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": {
            **_ow_base(),
            "ollama_model": "gemini-1.5-flash",
        },
    }
    errors = validate_project_config(app_config)
    assert any("google_api_key" in e for e in errors)


def test_validate_project_config_commercial_model_with_key_ok() -> None:
    """Config with gemini and google_api_key set passes."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": {
            **_ow_base(),
            "ollama_model": "gemini-1.5-flash",
            "google_api_key": "sk-fake",
        },
    }
    errors = validate_project_config(app_config)
    assert not any("google_api_key" in e and "required" in e for e in errors)


def test_available_providers_google_requires_key() -> None:
    """If available_providers contains google, google_api_key is required."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": {
            **_ow_base(),
            "available_providers": ["ollama", "google"],
        },
    }
    errors = validate_project_config(app_config)
    assert any("google_api_key" in e or ("model_providers" in e and "google" in e) for e in errors)


def test_available_providers_google_with_key_ok() -> None:
    """available_providers with google and google_api_key set passes."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": {
            **_ow_base(),
            "available_providers": ["ollama", "google"],
            "google_api_key": "sk-fake",
        },
    }
    errors = validate_project_config(app_config)
    assert not any("google_api_key" in e for e in errors)


def test_available_providers_invalid_value() -> None:
    """available_providers must contain only ollama, google, anthropic, openai."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": {
            **_ow_base(),
            "available_providers": ["unknown"],
        },
    }
    errors = validate_project_config(app_config)
    assert any("available_providers" in e and "one of" in e for e in errors)


def test_ollama_models_not_list() -> None:
    """ollama_models must be a list."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": {**_ow_base(), "ollama_models": "llama3.2"},
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "must be a list" in errors[0]


def test_ollama_models_element_not_string() -> None:
    """Each element must be a string."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": {**_ow_base(), "ollama_models": ["llama3.2", 123]},
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "ollama_models[1]" in errors[0]
    assert "non-empty string" in errors[0]


def test_ollama_models_empty_string_element() -> None:
    """Empty string element is invalid."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": {**_ow_base(), "ollama_models": ["llama3.2", ""]},
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "ollama_models[1]" in errors[0]


def test_ollama_models_whitespace_only_invalid() -> None:
    """Whitespace-only element is invalid."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": {**_ow_base(), "ollama_models": ["  "]},
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "ollama_models[0]" in errors[0]


def test_commands_policy_valid() -> None:
    """Valid commands_policy and lists add no errors (step 01)."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": {
            **_ow_base(),
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
        "ollama_workstation": {**_ow_base(), "commands_policy": "allow_all"},
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "commands_policy" in errors[0]
    assert "allow_by_default" in errors[0]


def test_allowed_commands_must_be_list() -> None:
    """allowed_commands must be a list."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": {**_ow_base(), "allowed_commands": "a.b"},
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "allowed_commands" in errors[0]
    assert "list" in errors[0]


def test_forbidden_commands_element_must_be_string() -> None:
    """forbidden_commands elements must be strings."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": {**_ow_base(), "forbidden_commands": ["a.b", 123]},
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "forbidden_commands[1]" in errors[0]


def test_command_discovery_interval_sec_valid() -> None:
    """command_discovery_interval_sec >= 0 is valid (step 03)."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": {**_ow_base(), "command_discovery_interval_sec": 60},
    }
    assert validate_project_config(app_config) == []


def test_command_discovery_interval_sec_negative_invalid() -> None:
    """command_discovery_interval_sec < 0 is invalid."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": {**_ow_base(), "command_discovery_interval_sec": -1},
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "command_discovery_interval_sec" in errors[0]


def test_model_calling_tool_allow_list_valid() -> None:
    """model_calling_tool_allow_list as list of strings is valid."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": {
            **_ow_base(),
            "model_calling_tool_allow_list": ["echo.proxy"],
        },
    }
    assert validate_project_config(app_config) == []


def test_model_calling_tool_allow_list_must_be_list() -> None:
    """model_calling_tool_allow_list must be a list."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": {**_ow_base(), "model_calling_tool_allow_list": "echo"},
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "model_calling_tool_allow_list" in errors[0]
    assert "list" in errors[0]


def test_redis_host_must_be_string() -> None:
    """redis_host when present must be a string."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": {**_ow_base(), "redis_host": 123},
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "redis_host" in errors[0]


def test_redis_key_prefix_must_be_string() -> None:
    """redis_key_prefix when present must be a string."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": {**_ow_base(), "redis_key_prefix": []},
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "redis_key_prefix" in errors[0]
