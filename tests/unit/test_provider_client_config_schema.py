"""
Unit tests for provider_client_config_schema (step_05).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from ollama_workstation.provider_client_config_schema import (  # noqa: E402
    ALLOWED_AUTH_KEYS,
    ALLOWED_FEATURES_KEYS,
    ALLOWED_LIMITS_KEYS,
    ALLOWED_TLS_KEYS,
    ALLOWED_TRANSPORT_KEYS,
    CANONICAL_PROVIDER_NAMES,
    PROVIDER_CLIENTS_TOP_LEVEL_KEYS,
    PROVIDER_SECTION_KEYS,
    get_empty_provider_clients_section,
    get_empty_provider_section,
    is_valid_provider_name,
    validate_provider_clients_structure,
)


def test_valid_minimal_structure_passes() -> None:
    """Minimal valid provider_clients with one provider and transport passes."""
    data: dict[str, Any] = {
        "default_provider": "ollama",
        "providers": {
            "ollama": {
                "transport": {"base_url": "http://localhost:11434"},
            },
        },
    }
    errors = validate_provider_clients_structure(data)
    assert errors == [], f"expected no errors, got {errors}"


def test_missing_default_provider_fails() -> None:
    """Missing default_provider is rejected."""
    data: dict[str, Any] = {"providers": {"ollama": {"transport": {}}}}
    errors = validate_provider_clients_structure(data)
    paths = [e[0] for e in errors]
    assert "provider_clients.default_provider" in paths


def test_missing_providers_fails() -> None:
    """Missing providers is rejected."""
    data: dict[str, Any] = {"default_provider": "ollama"}
    errors = validate_provider_clients_structure(data)
    paths = [e[0] for e in errors]
    assert any("providers" in p for p in paths)


def test_empty_providers_fails() -> None:
    """Empty providers dict is rejected."""
    data: dict[str, Any] = {"default_provider": "ollama", "providers": {}}
    errors = validate_provider_clients_structure(data)
    assert any("at least one provider" in e[1] for e in errors)


def test_disallowed_top_level_key_fails() -> None:
    """Unknown top-level key under provider_clients is rejected."""
    data: dict[str, Any] = {
        "default_provider": "ollama",
        "providers": {"ollama": {"transport": {}}},
        "unknown_key": 1,
    }
    errors = validate_provider_clients_structure(data)
    assert any("unknown_key" in e[0] and "disallowed" in e[1] for e in errors)


def test_disallowed_provider_section_key_fails() -> None:
    """Unknown key in provider section is rejected."""
    data: dict[str, Any] = {
        "default_provider": "ollama",
        "providers": {
            "ollama": {
                "transport": {},
                "unknown_section_key": 1,
            },
        },
    }
    errors = validate_provider_clients_structure(data)
    assert any("unknown_section_key" in e[0] for e in errors)


def test_disallowed_transport_key_fails() -> None:
    """Unknown key inside transport is rejected."""
    data: dict[str, Any] = {
        "default_provider": "ollama",
        "providers": {
            "ollama": {
                "transport": {"base_url": "http://x", "invalid_transport_key": 1},
            },
        },
    }
    errors = validate_provider_clients_structure(data)
    assert any("invalid_transport_key" in e[0] for e in errors)


def test_missing_transport_fails() -> None:
    """Provider section without transport is rejected."""
    data: dict[str, Any] = {
        "default_provider": "ollama",
        "providers": {"ollama": {"auth": {}}},
    }
    errors = validate_provider_clients_structure(data)
    assert any("transport" in e[0] and "required" in e[1] for e in errors)


def test_is_valid_provider_name_canonical() -> None:
    """Canonical provider names are valid."""
    for name in CANONICAL_PROVIDER_NAMES:
        assert is_valid_provider_name(name) is True


def test_is_valid_provider_name_custom_lowercase() -> None:
    """Lowercase alphanumeric + underscore custom names are valid."""
    assert is_valid_provider_name("custom_provider") is True
    assert is_valid_provider_name("abc123") is True


def test_is_valid_provider_name_invalid() -> None:
    """Invalid names are rejected."""
    assert is_valid_provider_name("") is False
    assert is_valid_provider_name("Has-Caps") is False
    assert is_valid_provider_name("with-hyphen") is False
    assert is_valid_provider_name("123leading") is False


def test_get_empty_provider_section_has_required_keys() -> None:
    """Template provider section contains all five subsection keys."""
    section = get_empty_provider_section()
    assert set(section.keys()) == PROVIDER_SECTION_KEYS
    assert section["transport"] == {}


def test_get_empty_provider_clients_section_structure() -> None:
    """Template provider_clients has default_provider and providers."""
    section = get_empty_provider_clients_section()
    assert set(section.keys()) == PROVIDER_CLIENTS_TOP_LEVEL_KEYS
    assert section["default_provider"] == ""
    assert section["providers"] == {}


def test_schema_constants_usable_by_validator_and_generator() -> None:
    """Allowed key sets are non-empty and cover standard."""
    assert "base_url" in ALLOWED_TRANSPORT_KEYS
    assert "api_key" in ALLOWED_AUTH_KEYS
    assert "verify" in ALLOWED_TLS_KEYS
    assert "supports_stream" in ALLOWED_FEATURES_KEYS
    assert "max_tokens" in ALLOWED_LIMITS_KEYS
