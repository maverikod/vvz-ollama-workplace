"""
Unit tests for provider_client_config_validator (step_06).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from ollama_workstation.provider_client_config_validator import (  # noqa: E402
    validate_config_provider_clients,
    validate_provider_clients,
    validate_provider_clients_or_raise,
)
from ollama_workstation.provider_errors import ValidationError  # noqa: E402


def _minimal_ollama() -> dict[str, Any]:
    """Minimal valid provider_clients with ollama (no auth, http)."""
    return {
        "default_provider": "ollama",
        "providers": {
            "ollama": {
                "transport": {"base_url": "http://localhost:11434"},
            },
        },
    }


def test_validate_provider_clients_valid_minimal_ollama() -> None:
    """Valid minimal ollama config passes."""
    errors = validate_provider_clients(_minimal_ollama())
    assert errors == [], f"expected no errors, got {errors}"


def test_validate_provider_clients_default_provider_not_in_providers() -> None:
    """default_provider must reference an existing provider (V4)."""
    data: dict[str, Any] = {
        "default_provider": "missing_provider",
        "providers": {"ollama": {"transport": {"base_url": "http://localhost:11434"}}},
    }
    errors = validate_provider_clients(data)
    assert any("not in providers" in e[1] for e in errors)
    assert any("default_provider" in e[0] for e in errors)


def test_validate_provider_clients_https_requires_tls() -> None:
    """Endpoint https:// requires tls section (V8/V10)."""
    data: dict[str, Any] = {
        "default_provider": "ollama",
        "providers": {
            "ollama": {
                "transport": {"base_url": "https://ollama.example.com"},
            },
        },
    }
    errors = validate_provider_clients(data)
    assert any("tls" in e[0] and "required" in e[1].lower() for e in errors)


def test_validate_provider_clients_https_with_tls_verify_false_conflict() -> None:
    """Secure endpoint with tls.verify false is rejected (V11)."""
    data: dict[str, Any] = {
        "default_provider": "ollama",
        "providers": {
            "ollama": {
                "transport": {"base_url": "https://ollama.example.com"},
                "tls": {"verify": False},
            },
        },
    }
    errors = validate_provider_clients(data)
    assert any("inconsistent" in e[1] or "verify" in e[1] for e in errors)


def test_validate_provider_clients_https_with_tls_ok() -> None:
    """Secure endpoint with tls section and verify true passes."""
    data: dict[str, Any] = {
        "default_provider": "ollama",
        "providers": {
            "ollama": {
                "transport": {"base_url": "https://ollama.example.com"},
                "tls": {"verify": True},
            },
        },
    }
    errors = validate_provider_clients(data)
    assert errors == [], f"expected no errors, got {errors}"


def test_validate_provider_clients_commercial_provider_requires_auth() -> None:
    """Commercial provider (e.g. openai) without auth fails (V6)."""
    data: dict[str, Any] = {
        "default_provider": "openai",
        "providers": {
            "openai": {
                "transport": {"base_url": "https://api.openai.com"},
                "tls": {"verify": True},
            },
        },
    }
    errors = validate_provider_clients(data)
    assert any("auth" in e[0] for e in errors)
    assert any("required" in e[1].lower() for e in errors)


def test_validate_provider_clients_commercial_provider_empty_auth_fails() -> None:
    """Commercial provider with empty auth section fails."""
    data: dict[str, Any] = {
        "default_provider": "openai",
        "providers": {
            "openai": {
                "transport": {"base_url": "https://api.openai.com"},
                "auth": {},
                "tls": {"verify": True},
            },
        },
    }
    errors = validate_provider_clients(data)
    assert any("auth" in e[0] for e in errors)


def test_validate_provider_clients_commercial_provider_with_api_key_ok() -> None:
    """Commercial provider with api_key passes."""
    data: dict[str, Any] = {
        "default_provider": "openai",
        "providers": {
            "openai": {
                "transport": {"base_url": "https://api.openai.com"},
                "auth": {"api_key": "sk-fake"},
                "tls": {"verify": True},
            },
        },
    }
    errors = validate_provider_clients(data)
    assert errors == [], f"expected no errors, got {errors}"


def test_validate_provider_clients_or_raise_valid() -> None:
    """validate_provider_clients_or_raise does not raise when valid."""
    validate_provider_clients_or_raise(_minimal_ollama())


def test_validate_provider_clients_or_raise_invalid_raises() -> None:
    """validate_provider_clients_or_raise raises ValidationError when invalid."""
    data: dict[str, Any] = {
        "default_provider": "ollama",
        "providers": {},
    }
    with pytest.raises(ValidationError) as exc_info:
        validate_provider_clients_or_raise(data)
    assert (
        "provider" in str(exc_info.value).lower()
        or "required" in str(exc_info.value).lower()
    )


def test_validate_config_provider_clients_missing_section() -> None:
    """validate_config_provider_clients returns error when provider_clients missing."""
    errors = validate_config_provider_clients({})
    assert any("provider_clients" in e[0] for e in errors)
    assert any("required" in e[1].lower() for e in errors)


def test_validate_config_provider_clients_valid() -> None:
    """validate_config_provider_clients passes when section valid."""
    app_config = {"provider_clients": _minimal_ollama()}
    errors = validate_config_provider_clients(app_config)
    assert errors == [], f"expected no errors, got {errors}"


def test_validate_config_provider_clients_not_dict() -> None:
    """validate_config_provider_clients rejects non-dict config."""
    errors = validate_config_provider_clients([])
    assert len(errors) == 1
    assert "object" in errors[0][1].lower()


def test_structure_errors_from_schema_still_reported() -> None:
    """Structure errors (missing transport, etc.) still come from schema."""
    data: dict[str, Any] = {
        "default_provider": "ollama",
        "providers": {"ollama": {"auth": {}}},  # missing transport
    }
    errors = validate_provider_clients(data)
    assert any("transport" in e[0] and "required" in e[1] for e in errors)


def test_wss_requires_tls() -> None:
    """wss:// endpoint requires tls section."""
    data: dict[str, Any] = {
        "default_provider": "ollama",
        "providers": {
            "ollama": {
                "transport": {"base_url": "wss://ollama.example.com"},
            },
        },
    }
    errors = validate_provider_clients(data)
    assert any("tls" in e[0] for e in errors)
