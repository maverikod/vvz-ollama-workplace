"""
Unit tests for provider_client_config_generator (step_07).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from ollama_workstation.provider_client_config_generator import (  # noqa: E402
    generate_full_config_with_provider_clients,
    generate_provider_clients_section,
    generate_sample,
    get_default_ollama_provider_section,
)
from ollama_workstation.provider_client_config_validator import (  # noqa: E402
    validate_provider_clients,
    validate_provider_clients_or_raise,
)


def test_generate_provider_clients_section_passes_validator() -> None:
    """Generator produces output that passes the provider client config validator."""
    section = generate_provider_clients_section(validate=True)
    errors = validate_provider_clients(section)
    assert errors == [], f"expected no errors, got {errors}"


def test_generate_provider_clients_section_validate_or_raise() -> None:
    """Generated section passes validate_provider_clients_or_raise."""
    section = generate_provider_clients_section(validate=True)
    validate_provider_clients_or_raise(section)


def test_generate_sample_includes_ollama_with_all_subsections() -> None:
    """Sample includes ollama with transport/auth/tls/features/limits per standard."""
    section = generate_sample(validate=True)
    assert section.get("default_provider") == "ollama"
    providers = section.get("providers", {})
    assert "ollama" in providers
    ollama = providers["ollama"]
    assert "transport" in ollama and isinstance(ollama["transport"], dict)
    assert "auth" in ollama and isinstance(ollama["auth"], dict)
    assert "tls" in ollama and isinstance(ollama["tls"], dict)
    assert "features" in ollama and isinstance(ollama["features"], dict)
    assert "limits" in ollama and isinstance(ollama["limits"], dict)
    assert "base_url" in ollama["transport"]
    assert "protocol" in ollama["transport"]


def test_get_default_ollama_provider_section_structure() -> None:
    """Default ollama section has all required and optional keys per standard."""
    section = get_default_ollama_provider_section()
    assert "transport" in section
    assert section["transport"].get("base_url") == "http://localhost:11434"
    assert section["transport"].get("protocol") == "http"
    assert "auth" in section
    assert "tls" in section
    assert "features" in section
    assert "limits" in section
    assert section["features"].get("supports_embeddings") is True


def test_generate_provider_clients_section_custom_providers() -> None:
    """Generator accepts custom providers dict and default_provider must be in it."""
    custom: dict[str, Any] = {
        "ollama": get_default_ollama_provider_section(
            base_url="http://127.0.0.1:11434"
        ),
    }
    section = generate_provider_clients_section(
        default_provider="ollama",
        providers=custom,
        validate=True,
    )
    assert section["default_provider"] == "ollama"
    assert (
        section["providers"]["ollama"]["transport"]["base_url"]
        == "http://127.0.0.1:11434"
    )


def test_generate_provider_clients_section_default_provider_missing_raises() -> None:
    """Generator raises if default_provider is not in providers."""
    with pytest.raises(ValueError, match="must exist in providers"):
        generate_provider_clients_section(
            default_provider="ollama",
            providers={"openai": get_default_ollama_provider_section()},
            validate=False,
        )


def test_generate_full_config_with_provider_clients() -> None:
    """Full config dict contains provider_clients key."""
    section = generate_provider_clients_section(validate=True)
    full = generate_full_config_with_provider_clients(section)
    assert full["provider_clients"] == section


def test_generate_sample_full_config() -> None:
    """generate_sample(full_config=True) returns dict with provider_clients key."""
    full = generate_sample(full_config=True, validate=True)
    assert "provider_clients" in full
    validate_provider_clients_or_raise(full["provider_clients"])
