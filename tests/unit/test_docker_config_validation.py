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
    get_runtime_allowed_providers,
    validate_commercial_model_keys,
    validate_model_providers,
    validate_project_config,
)


def _ow_base() -> dict:
    """Minimal ollama_workstation with required ollama section."""
    return {"ollama": {"base_url": "http://localhost:11434", "model": "m"}}


def _pc_ollama_only() -> dict:
    """Minimal provider_clients for model-workspace (ollama only)."""
    return {
        "default_provider": "ollama",
        "providers": {
            "ollama": {
                "transport": {
                    "base_url": "http://localhost:11434",
                    "protocol": "http",
                    "request_timeout_seconds": 120,
                },
                "auth": {},
                "tls": {},
                "features": {},
                "limits": {},
            }
        },
    }


def test_ollama_models_valid_list() -> None:
    """Valid ollama.models (list of non-empty strings) adds no errors."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_ollama_only(),
        "ollama_workstation": {
            **_ow_base(),
            "ollama": {**_ow_base()["ollama"], "models": ["llama3.2", "qwen3"]},
        },
    }
    assert validate_project_config(app_config) == []


def test_ollama_models_empty_list() -> None:
    """Empty models list is valid."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_ollama_only(),
        "ollama_workstation": {
            **_ow_base(),
            "ollama": {**_ow_base()["ollama"], "models": []},
        },
    }
    assert validate_project_config(app_config) == []


def test_ollama_models_missing_key() -> None:
    """Missing ollama.models is valid (optional)."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_ollama_only(),
        "ollama_workstation": _ow_base(),
    }
    assert validate_project_config(app_config) == []


def test_ollama_section_required() -> None:
    """ollama_workstation.ollama is required."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_ollama_only(),
        "ollama_workstation": {},
    }
    errors = validate_project_config(app_config)
    assert len(errors) >= 1
    assert "ollama" in errors[0]


def test_ollama_base_url_or_model_server_url_required() -> None:
    """ollama_workstation.ollama must be an object (model-workspace)."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_ollama_only(),
        "ollama_workstation": {"ollama": {"model": "m"}},
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 0 or "ollama" in str(errors)


def test_legacy_flat_api_key_forbidden_for_model_workspace() -> None:
    """Flat google_api_key (and other legacy keys) forbidden for model-workspace."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_ollama_only(),
        "ollama_workstation": {
            **_ow_base(),
            "google_api_key": "sk-fake",
        },
    }
    errors = validate_project_config(app_config)
    assert any("google_api_key" in e and "forbidden" in e for e in errors)


def test_legacy_provider_urls_forbidden_for_model_workspace() -> None:
    """ollama_workstation.provider_urls is forbidden for model-workspace."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_ollama_only(),
        "ollama_workstation": {
            **_ow_base(),
            "provider_urls": {"ollama": "http://localhost:11434"},
        },
    }
    errors = validate_project_config(app_config)
    assert any("provider_urls" in e and "forbidden" in e for e in errors)


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


def test_model_workspace_without_provider_clients_fails() -> None:
    """model-workspace without provider_clients fails (no autogeneration)."""
    app_config = {
        "server": {"protocol": "http"},
        "ollama_workstation": {
            **_ow_base(),
            "ollama": {**_ow_base()["ollama"], "model": "gemini-1.5-flash"},
        },
    }
    errors = validate_project_config(app_config)
    assert any("provider_clients" in e and "required" in e for e in errors)


def test_provider_clients_commercial_without_auth_fails() -> None:
    """provider_clients with commercial provider (google) without auth fails."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": {
            "default_provider": "ollama",
            "providers": {
                "ollama": {
                    "transport": {
                        "base_url": "http://localhost:11434",
                        "protocol": "http",
                        "request_timeout_seconds": 120,
                    },
                    "auth": {},
                    "tls": {},
                    "features": {},
                    "limits": {},
                },
                "google": {
                    "transport": {
                        "base_url": "https://generativelanguage.googleapis.com/v1/",
                        "protocol": "https",
                        "request_timeout_seconds": 120,
                    },
                    "auth": {},
                    "tls": {},
                    "features": {},
                    "limits": {},
                },
            },
        },
        "ollama_workstation": _ow_base(),
    }
    errors = validate_project_config(app_config)
    assert any("google" in e and ("auth" in e or "api_key" in e) for e in errors)


def test_validate_project_config_commercial_with_key_ok() -> None:
    """Config with provider_clients including google and auth passes."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": {
            "default_provider": "ollama",
            "providers": {
                "ollama": _pc_ollama_only()["providers"]["ollama"],
                "google": {
                    "transport": {
                        "base_url": "https://generativelanguage.googleapis.com/v1/",
                        "protocol": "https",
                        "request_timeout_seconds": 120,
                    },
                    "auth": {"api_key": "sk-fake"},
                    "tls": {"verify": True},
                    "features": {},
                    "limits": {},
                },
            },
        },
        "ollama_workstation": _ow_base(),
    }
    errors = validate_project_config(app_config)
    assert not any("google" in e and "auth" in e for e in errors)


def test_available_providers_google_requires_key() -> None:
    """provider_clients with google without auth fails (runtime-allowed commercial)."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": {
            "default_provider": "ollama",
            "providers": {
                "ollama": _pc_ollama_only()["providers"]["ollama"],
                "google": {
                    "transport": {
                        "base_url": "https://generativelanguage.googleapis.com/v1/",
                        "protocol": "https",
                        "request_timeout_seconds": 120,
                    },
                    "auth": {},
                    "tls": {},
                    "features": {},
                    "limits": {},
                },
            },
        },
        "ollama_workstation": {
            **_ow_base(),
            "available_providers": ["ollama", "google"],
        },
    }
    errors = validate_project_config(app_config)
    assert any("google" in e and "auth" in e for e in errors)


def test_available_providers_google_with_key_ok() -> None:
    """provider_clients with google and auth passes."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": {
            "default_provider": "ollama",
            "providers": {
                "ollama": _pc_ollama_only()["providers"]["ollama"],
                "google": {
                    "transport": {
                        "base_url": "https://generativelanguage.googleapis.com/v1/",
                        "protocol": "https",
                        "request_timeout_seconds": 120,
                    },
                    "auth": {"api_key": "sk-fake"},
                    "tls": {"verify": True},
                    "features": {},
                    "limits": {},
                },
            },
        },
        "ollama_workstation": {
            **_ow_base(),
            "available_providers": ["ollama", "google"],
        },
    }
    assert validate_project_config(app_config) == []


def test_available_providers_invalid_value() -> None:
    """available_providers must contain only ollama, google, anthropic, openai."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_ollama_only(),
        "ollama_workstation": {
            **_ow_base(),
            "available_providers": ["unknown"],
        },
    }
    errors = validate_project_config(app_config)
    assert any("available_providers" in e and "one of" in e for e in errors)


def test_ollama_models_not_list() -> None:
    """ollama.models must be a list."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_ollama_only(),
        "ollama_workstation": {
            **_ow_base(),
            "ollama": {**_ow_base()["ollama"], "models": "llama3.2"},
        },
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "must be a list" in errors[0]


def test_ollama_models_element_not_string() -> None:
    """Each element must be a string."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_ollama_only(),
        "ollama_workstation": {
            **_ow_base(),
            "ollama": {**_ow_base()["ollama"], "models": ["llama3.2", 123]},
        },
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "ollama.models[1]" in errors[0]
    assert "non-empty string" in errors[0]


def test_ollama_models_empty_string_element() -> None:
    """Empty string element is invalid."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_ollama_only(),
        "ollama_workstation": {
            **_ow_base(),
            "ollama": {**_ow_base()["ollama"], "models": ["llama3.2", ""]},
        },
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "ollama.models[1]" in errors[0]


def test_ollama_models_whitespace_only_invalid() -> None:
    """Whitespace-only element is invalid."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_ollama_only(),
        "ollama_workstation": {
            **_ow_base(),
            "ollama": {**_ow_base()["ollama"], "models": ["  "]},
        },
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "ollama.models[0]" in errors[0]


def test_commands_policy_valid() -> None:
    """Valid commands_policy and lists add no errors (step 01)."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_ollama_only(),
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
        "provider_clients": _pc_ollama_only(),
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
        "provider_clients": _pc_ollama_only(),
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
        "provider_clients": _pc_ollama_only(),
        "ollama_workstation": {**_ow_base(), "forbidden_commands": ["a.b", 123]},
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "forbidden_commands[1]" in errors[0]


def test_command_discovery_interval_sec_valid() -> None:
    """command_discovery_interval_sec >= 0 is valid (step 03)."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_ollama_only(),
        "ollama_workstation": {**_ow_base(), "command_discovery_interval_sec": 60},
    }
    assert validate_project_config(app_config) == []


def test_command_discovery_interval_sec_negative_invalid() -> None:
    """command_discovery_interval_sec < 0 is invalid."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_ollama_only(),
        "ollama_workstation": {**_ow_base(), "command_discovery_interval_sec": -1},
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "command_discovery_interval_sec" in errors[0]


def test_model_calling_tool_allow_list_valid() -> None:
    """model_calling_tool_allow_list as list of strings is valid."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_ollama_only(),
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
        "provider_clients": _pc_ollama_only(),
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
        "provider_clients": _pc_ollama_only(),
        "ollama_workstation": {**_ow_base(), "redis_host": 123},
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "redis_host" in errors[0]


def test_redis_key_prefix_must_be_string() -> None:
    """redis_key_prefix when present must be a string."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_ollama_only(),
        "ollama_workstation": {**_ow_base(), "redis_key_prefix": []},
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "redis_key_prefix" in errors[0]


# --- Runtime-allowed providers and fail-fast commercial validation ---


def test_ollama_only_config_passes() -> None:
    """Ollama-only provider_clients (no commercial in providers) passes."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_ollama_only(),
        "ollama_workstation": {
            **_ow_base(),
            "ollama": {**_ow_base()["ollama"], "model": "llama3.2", "models": []},
        },
    }
    assert validate_project_config(app_config) == []


def test_ollama_only_with_available_providers_ollama_only_passes() -> None:
    """available_providers only ollama with provider_clients ollama-only passes."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_ollama_only(),
        "ollama_workstation": {
            **_ow_base(),
            "available_providers": ["ollama"],
        },
    }
    assert validate_project_config(app_config) == []


def test_runtime_allowed_commercial_url_but_no_key_fails() -> None:
    """provider_clients with google (commercial) without auth fails."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": {
            "default_provider": "ollama",
            "providers": {
                "ollama": _pc_ollama_only()["providers"]["ollama"],
                "google": {
                    "transport": {
                        "base_url": "https://generativelanguage.googleapis.com/v1beta/",
                        "protocol": "https",
                        "request_timeout_seconds": 120,
                    },
                    "auth": {},
                    "tls": {},
                    "features": {},
                    "limits": {},
                },
            },
        },
        "ollama_workstation": {
            **_ow_base(),
            "available_providers": ["ollama", "google"],
        },
    }
    errors = validate_project_config(app_config)
    assert any("google" in e and "auth" in e for e in errors), (
        "expected error for google when in provider_clients without auth: %s" % errors
    )


def test_config_path_in_commercial_validation_errors() -> None:
    """Validation errors for commercial providers include config path."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": {
            "default_provider": "ollama",
            "providers": {
                "ollama": _pc_ollama_only()["providers"]["ollama"],
                "google": {
                    "transport": {
                        "base_url": "https://generativelanguage.googleapis.com/v1/",
                        "protocol": "https",
                        "request_timeout_seconds": 120,
                    },
                    "auth": {},
                    "tls": {},
                    "features": {},
                    "limits": {},
                },
            },
        },
        "ollama_workstation": {
            **_ow_base(),
            "available_providers": ["google"],
        },
    }
    errors = validate_project_config(app_config)
    assert errors
    assert any("provider_clients" in e or "google" in e for e in errors)


def test_provider_clients_providers_expand_runtime_allowed() -> None:
    """provider_clients.providers keys are runtime-allowed; commercial requires auth."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": {
            "default_provider": "ollama",
            "providers": {
                "ollama": {
                    "transport": {
                        "base_url": "http://localhost:11434",
                        "protocol": "http",
                        "request_timeout_seconds": 120,
                    },
                    "auth": {},
                    "tls": {},
                    "features": {},
                    "limits": {},
                },
                "google": {
                    "transport": {
                        "base_url": "https://google.com/v1",
                        "protocol": "https",
                        "request_timeout_seconds": 120,
                    },
                    "auth": {},
                    "tls": {},
                    "features": {},
                    "limits": {},
                },
            },
        },
        "ollama_workstation": _ow_base(),
    }
    errors = validate_project_config(app_config)
    assert any("google" in e and "auth" in e for e in errors), (
        "expected error for google when in provider_clients.providers without auth: %s"
        % errors
    )


def test_get_runtime_allowed_providers_from_available_and_models() -> None:
    """get_runtime_allowed_providers merges available_providers and model ids."""
    app_config = {
        "ollama_workstation": {
            "ollama": {
                "base_url": "http://localhost:11434",
                "model": "gemini-2.0-flash",
                "models": ["llama3.2"],
            },
            "available_providers": ["anthropic"],
        },
    }
    providers = get_runtime_allowed_providers(app_config)
    assert "google" in providers
    assert "ollama" in providers
    assert "anthropic" in providers


def test_get_runtime_allowed_providers_includes_provider_clients_keys() -> None:
    """get_runtime_allowed_providers includes provider_clients.providers keys."""
    app_config = {
        "ollama_workstation": _ow_base(),
        "provider_clients": {
            "default_provider": "ollama",
            "providers": {"ollama": {}, "openai": {}},
        },
    }
    providers = get_runtime_allowed_providers(app_config)
    assert "openai" in providers
    assert "ollama" in providers


def test_validate_model_providers_without_app_config_backward_compat() -> None:
    """validate_model_providers without app_config still runs (backward compat)."""
    ow = {
        **_ow_base(),
        "available_providers": ["ollama"],
    }
    errors = validate_model_providers(ow, "llama3.2", [])
    assert errors == []
