"""
Unit tests for provider_registry (step_09).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from ollama_workstation.provider_client_base import BaseProviderClient  # noqa: E402
from ollama_workstation.provider_errors import ValidationError  # noqa: E402
from ollama_workstation.provider_registry import (  # noqa: E402
    get_client,
    get_client_from_app_config,
    get_default_client,
    list_supported_providers,
)


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


def test_get_client_invalid_config_raises() -> None:
    """Invalid config with validate=True leads to ValidationError; no client created."""
    invalid = {"default_provider": "ollama", "providers": {}}
    with pytest.raises(ValidationError) as exc_info:
        get_client("ollama", invalid, validate=True)
    assert (
        "providers" in str(exc_info.value).lower()
        or "required" in str(exc_info.value).lower()
    )


def test_get_client_unknown_provider_raises() -> None:
    """Valid config but unsupported provider name raises clear ValidationError."""
    data = _minimal_ollama()
    data["providers"]["openai"] = {
        "transport": {"base_url": "https://api.openai.com"},
    }
    with pytest.raises(ValidationError) as exc_info:
        get_client("openai", data, validate=True)
    assert "not implemented" in str(exc_info.value).lower() or "openai" in str(
        exc_info.value
    )


def test_get_client_provider_not_in_providers_raises() -> None:
    """Provider name not in providers raises ValidationError."""
    data = _minimal_ollama()
    with pytest.raises(ValidationError) as exc_info:
        get_client("anthropic", data, validate=True)
    assert "not in" in str(exc_info.value).lower() or "anthropic" in str(exc_info.value)


def test_get_default_client_invalid_config_raises() -> None:
    """get_default_client with invalid config raises ValidationError."""
    invalid = {"default_provider": "x", "providers": {}}
    with pytest.raises(ValidationError):
        get_default_client(invalid, validate=True)


def test_get_default_client_missing_default_raises() -> None:
    """get_default_client with empty default_provider raises ValidationError."""
    data: dict[str, Any] = {
        "default_provider": "",
        "providers": {"ollama": {"transport": {"base_url": "http://localhost:11434"}}},
    }
    with pytest.raises(ValidationError) as exc_info:
        get_default_client(data, validate=False)
    assert "default_provider" in str(exc_info.value).lower()


def test_get_client_from_app_config_missing_section_raises() -> None:
    """get_client_from_app_config without provider_clients raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        get_client_from_app_config({})
    assert "provider_clients" in str(exc_info.value).lower()


def test_get_client_from_app_config_default_provider() -> None:
    """With provider_name=None returns default client or clear error."""
    app_config = {"provider_clients": _minimal_ollama()}
    try:
        client = get_client_from_app_config(app_config, provider_name=None)
        assert isinstance(client, BaseProviderClient)
    except ValidationError as e:
        # Step_08 may not be done: ollama client not available
        assert "not available" in str(e).lower() or "not implemented" in str(e).lower()


def test_list_supported_providers_includes_ollama() -> None:
    """list_supported_providers returns at least ollama (phase 1)."""
    supported = list_supported_providers()
    assert isinstance(supported, tuple)
    assert "ollama" in supported


def test_get_client_ollama_returns_client_or_raises_clear() -> None:
    """get_client('ollama', valid_config) returns client or clear ValidationError."""
    data = _minimal_ollama()
    try:
        client = get_client("ollama", data, validate=True)
        assert isinstance(client, BaseProviderClient)
    except ValidationError as e:
        assert "not available" in str(e).lower() or "not implemented" in str(e).lower()


def test_get_client_empty_provider_name_raises() -> None:
    """get_client with empty provider_name raises ValidationError."""
    data = _minimal_ollama()
    with pytest.raises(ValidationError) as exc_info:
        get_client("", data, validate=False)
    assert (
        "non-empty" in str(exc_info.value).lower()
        or "provider" in str(exc_info.value).lower()
    )
