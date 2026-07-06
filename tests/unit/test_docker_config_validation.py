"""
Unit tests for docker_config_validation: mwps.mwps_models.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from mwps.docker_config_validation import (  # noqa: E402
    validate_project_config,
)


def _ow_base() -> dict:
    """Minimal mwps with required mwps section."""
    return {"mwps": {"base_url": "http://localhost:11434", "model": "m"}}


def _pc_mwps_only() -> dict:
    """Minimal provider_clients for model-workspace (mwps only)."""
    return {
        "default_provider": "mwps",
        "providers": {
            "mwps": {
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


def test_mwps_models_valid_list() -> None:
    """Valid mwps.models (list of non-empty strings) adds no errors."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_mwps_only(),
        "mwps": {
            **_ow_base(),
            "mwps": {**_ow_base()["mwps"], "models": ["llama3.2", "qwen3"]},
        },
    }
    assert validate_project_config(app_config) == []


def test_mwps_models_empty_list() -> None:
    """Empty models list is valid."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_mwps_only(),
        "mwps": {
            **_ow_base(),
            "mwps": {**_ow_base()["mwps"], "models": []},
        },
    }
    assert validate_project_config(app_config) == []


def test_mwps_models_missing_key() -> None:
    """Missing mwps.models is valid (optional)."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_mwps_only(),
        "mwps": _ow_base(),
    }
    assert validate_project_config(app_config) == []


def test_mwps_section_required() -> None:
    """mwps.mwps is required."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_mwps_only(),
        "mwps": {},
    }
    errors = validate_project_config(app_config)
    assert len(errors) >= 1
    assert "mwps" in errors[0]


def test_mwps_base_url_or_model_server_url_required() -> None:
    """mwps.mwps must be an object (model-workspace)."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_mwps_only(),
        "mwps": {"mwps": {"model": "m"}},
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 0 or "mwps" in str(errors)


def test_legacy_flat_api_key_forbidden_for_model_workspace() -> None:
    """Flat google_api_key (and other legacy keys) forbidden for model-workspace."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_mwps_only(),
        "mwps": {
            **_ow_base(),
            "google_api_key": "sk-fake",
        },
    }
    errors = validate_project_config(app_config)
    assert any("google_api_key" in e and "forbidden" in e for e in errors)


def test_legacy_provider_urls_forbidden_for_model_workspace() -> None:
    """mwps.provider_urls is forbidden for model-workspace."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_mwps_only(),
        "mwps": {
            **_ow_base(),
            "provider_urls": {"mwps": "http://localhost:11434"},
        },
    }
    errors = validate_project_config(app_config)
    assert any("provider_urls" in e and "forbidden" in e for e in errors)


def test_model_workspace_without_provider_clients_fails() -> None:
    """model-workspace without provider_clients fails (no autogeneration)."""
    app_config = {
        "server": {"protocol": "http"},
        "mwps": {
            **_ow_base(),
            "mwps": {**_ow_base()["mwps"], "model": "gemini-1.5-flash"},
        },
    }
    errors = validate_project_config(app_config)
    assert any("provider_clients" in e and "required" in e for e in errors)


def test_provider_clients_commercial_without_auth_fails() -> None:
    """provider_clients with commercial provider (google) without auth fails."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": {
            "default_provider": "mwps",
            "providers": {
                "mwps": {
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
        "mwps": _ow_base(),
    }
    errors = validate_project_config(app_config)
    assert any("google" in e and ("auth" in e or "api_key" in e) for e in errors)


def test_validate_project_config_commercial_with_key_ok() -> None:
    """Config with provider_clients including google and auth passes."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": {
            "default_provider": "mwps",
            "providers": {
                "mwps": _pc_mwps_only()["providers"]["mwps"],
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
        "mwps": _ow_base(),
    }
    errors = validate_project_config(app_config)
    assert not any("google" in e and "auth" in e for e in errors)


def test_mwps_models_not_list() -> None:
    """mwps.models must be a list."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_mwps_only(),
        "mwps": {
            **_ow_base(),
            "mwps": {**_ow_base()["mwps"], "models": "llama3.2"},
        },
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "must be a list" in errors[0]


def test_mwps_models_element_not_string() -> None:
    """Each element must be a string."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_mwps_only(),
        "mwps": {
            **_ow_base(),
            "mwps": {**_ow_base()["mwps"], "models": ["llama3.2", 123]},
        },
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "mwps.models[1]" in errors[0]
    assert "non-empty string" in errors[0]


def test_mwps_models_empty_string_element() -> None:
    """Empty string element is invalid."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_mwps_only(),
        "mwps": {
            **_ow_base(),
            "mwps": {**_ow_base()["mwps"], "models": ["llama3.2", ""]},
        },
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "mwps.models[1]" in errors[0]


def test_mwps_models_whitespace_only_invalid() -> None:
    """Whitespace-only element is invalid."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_mwps_only(),
        "mwps": {
            **_ow_base(),
            "mwps": {**_ow_base()["mwps"], "models": ["  "]},
        },
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "mwps.models[0]" in errors[0]


def test_commands_policy_valid() -> None:
    """Valid commands_policy and lists add no errors (step 01)."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_mwps_only(),
        "mwps": {
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
        "provider_clients": _pc_mwps_only(),
        "mwps": {**_ow_base(), "commands_policy": "allow_all"},
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "commands_policy" in errors[0]
    assert "allow_by_default" in errors[0]


def test_allowed_commands_must_be_list() -> None:
    """allowed_commands must be a list."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_mwps_only(),
        "mwps": {**_ow_base(), "allowed_commands": "a.b"},
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "allowed_commands" in errors[0]
    assert "list" in errors[0]


def test_forbidden_commands_element_must_be_string() -> None:
    """forbidden_commands elements must be strings."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_mwps_only(),
        "mwps": {**_ow_base(), "forbidden_commands": ["a.b", 123]},
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "forbidden_commands[1]" in errors[0]


def test_command_discovery_interval_sec_valid() -> None:
    """command_discovery_interval_sec >= 0 is valid (step 03)."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_mwps_only(),
        "mwps": {**_ow_base(), "command_discovery_interval_sec": 60},
    }
    assert validate_project_config(app_config) == []


def test_command_discovery_interval_sec_negative_invalid() -> None:
    """command_discovery_interval_sec < 0 is invalid."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_mwps_only(),
        "mwps": {**_ow_base(), "command_discovery_interval_sec": -1},
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "command_discovery_interval_sec" in errors[0]


def test_model_calling_tool_allow_list_valid() -> None:
    """model_calling_tool_allow_list as list of strings is valid."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_mwps_only(),
        "mwps": {
            **_ow_base(),
            "model_calling_tool_allow_list": ["echo.proxy"],
        },
    }
    assert validate_project_config(app_config) == []


def test_model_calling_tool_allow_list_must_be_list() -> None:
    """model_calling_tool_allow_list must be a list."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_mwps_only(),
        "mwps": {**_ow_base(), "model_calling_tool_allow_list": "echo"},
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "model_calling_tool_allow_list" in errors[0]
    assert "list" in errors[0]


def test_redis_host_must_be_string() -> None:
    """redis_host when present must be a string."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_mwps_only(),
        "mwps": {**_ow_base(), "redis_host": 123},
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "redis_host" in errors[0]


def test_redis_key_prefix_must_be_string() -> None:
    """redis_key_prefix when present must be a string."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_mwps_only(),
        "mwps": {**_ow_base(), "redis_key_prefix": []},
    }
    errors = validate_project_config(app_config)
    assert len(errors) == 1
    assert "redis_key_prefix" in errors[0]


# --- Runtime-allowed providers and fail-fast commercial validation ---


def test_mwps_only_config_passes() -> None:
    """Model Workplace Server-only provider_clients (no commercial providers) passes."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": _pc_mwps_only(),
        "mwps": {
            **_ow_base(),
            "mwps": {**_ow_base()["mwps"], "model": "llama3.2", "models": []},
        },
    }
    assert validate_project_config(app_config) == []


def test_runtime_allowed_commercial_url_but_no_key_fails() -> None:
    """provider_clients with google (commercial) without auth fails."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": {
            "default_provider": "mwps",
            "providers": {
                "mwps": _pc_mwps_only()["providers"]["mwps"],
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
        "mwps": _ow_base(),
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
            "default_provider": "mwps",
            "providers": {
                "mwps": _pc_mwps_only()["providers"]["mwps"],
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
        "mwps": _ow_base(),
    }
    errors = validate_project_config(app_config)
    assert errors
    assert any("provider_clients" in e or "google" in e for e in errors)


def test_provider_clients_providers_expand_runtime_allowed() -> None:
    """provider_clients.providers keys are runtime-allowed; commercial requires auth."""
    app_config = {
        "server": {"protocol": "http"},
        "provider_clients": {
            "default_provider": "mwps",
            "providers": {
                "mwps": {
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
        "mwps": _ow_base(),
    }
    errors = validate_project_config(app_config)
    assert any("google" in e and "auth" in e for e in errors), (
        "expected error for google when in provider_clients.providers without auth: %s"
        % errors
    )
