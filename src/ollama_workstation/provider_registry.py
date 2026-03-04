"""
Registry and factory for provider clients.

Given provider name and validated provider_clients config, returns the
appropriate provider client instance (BaseProviderClient). Config-driven:
active provider and provider_clients sections used to build clients;
validation errors from step_06 prevent creating invalid clients.
Workstation orchestration can resolve client by default_provider or by
explicit provider name. See step_09_provider_client_registry.md and
SCOPE_FREEZE (provider_registry.py).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from typing import Any, Callable

from ollama_workstation.provider_client_base import BaseProviderClient
from ollama_workstation.provider_client_config_validator import (
    validate_provider_clients_or_raise,
)
from ollama_workstation.provider_errors import ValidationError


def _build_ollama(provider_section: Any) -> BaseProviderClient:
    """
    Build Ollama provider client from provider section dict.

    Lazy import so step_08 can be merged after step_09. If ollama_provider_client
    is missing, raises ValidationError with clear message.
    """
    try:
        from ollama_workstation.ollama_provider_client import OllamaProviderClient
    except ImportError as e:
        raise ValidationError(
            "Provider client for 'ollama' is not available "
            "(ollama_provider_client module not implemented or not installed).",
            cause=e,
        ) from e
    if not isinstance(provider_section, dict):
        raise ValidationError(
            "provider_section for ollama must be a dict, got "
            f"{type(provider_section).__name__}"
        )
    return OllamaProviderClient(provider_section)


# Map: provider name (config key) -> builder(provider_section) -> BaseProviderClient.
# Only providers with implemented clients are registered; unknown name -> clear error.
_PROVIDER_BUILDERS: dict[str, Callable[[Any], BaseProviderClient]] = {
    "ollama": _build_ollama,
}


def get_client(
    provider_name: str,
    provider_clients_data: Any,
    *,
    validate: bool = True,
) -> BaseProviderClient:
    """
    Return a provider client instance for the given provider name.

    Uses provider_clients_data["providers"][provider_name] as the provider
    section. If validate is True (default), runs step_06 validation first;
    invalid config raises ValidationError and no client is created.

    Args:
        provider_name: Config key of the provider (e.g. "ollama").
        provider_clients_data: Full provider_clients section (dict with
            default_provider and providers).
        validate: If True, call validate_provider_clients_or_raise before
            building.

    Returns:
        A provider client implementing BaseProviderClient.

    Raises:
        ValidationError: If validate is True and config is invalid; or if
            provider_name is missing from providers; or if no builder is
            registered for provider_name (not implemented).
    """
    if validate:
        validate_provider_clients_or_raise(provider_clients_data)

    if not isinstance(provider_clients_data, dict):
        raise ValidationError(
            "provider_clients_data must be a dict, got "
            f"{type(provider_clients_data).__name__}"
        )
    providers = provider_clients_data.get("providers")
    if not isinstance(providers, dict):
        raise ValidationError(
            "provider_clients.providers is required and must be an object"
        )
    name = (provider_name or "").strip()
    if not name:
        raise ValidationError("provider_name must be non-empty")
    if name not in providers:
        raise ValidationError(
            f"provider '{name}' not in provider_clients.providers; "
            f"available: {sorted(providers.keys())}"
        )
    builder = _PROVIDER_BUILDERS.get(name)
    if builder is None:
        raise ValidationError(
            f"Provider client for '{name}' is not implemented; "
            f"supported: {sorted(_PROVIDER_BUILDERS.keys())}"
        )
    section = providers[name]
    return builder(section)


def get_default_client(
    provider_clients_data: Any,
    *,
    validate: bool = True,
) -> BaseProviderClient:
    """
    Return the provider client for the default provider.

    Reads default_provider from provider_clients_data and returns
    get_client(default_provider, provider_clients_data, validate=validate).

    Raises:
        ValidationError: If config is invalid or default_provider is missing
            or has no registered builder.
    """
    if validate:
        validate_provider_clients_or_raise(provider_clients_data)
    if not isinstance(provider_clients_data, dict):
        raise ValidationError(
            "provider_clients_data must be a dict, got "
            f"{type(provider_clients_data).__name__}"
        )
    default = (provider_clients_data.get("default_provider") or "").strip()
    if not default:
        raise ValidationError(
            "provider_clients.default_provider is required and must be non-empty"
        )
    return get_client(default, provider_clients_data, validate=False)


def get_client_from_app_config(
    app_config: Any,
    provider_name: str | None = None,
    *,
    validate: bool = True,
) -> BaseProviderClient:
    """
    Extract provider_clients from full app config and return a client.

    If provider_name is None, returns the default provider client.
    Otherwise returns the client for the given provider name.

    Args:
        app_config: Full application config dict (must contain
            provider_clients section).
        provider_name: Optional explicit provider; if None, use
            default_provider.
        validate: If True, validate provider_clients before building.

    Returns:
        A provider client for the requested or default provider.

    Raises:
        ValidationError: If provider_clients section is missing, invalid,
            or provider not available.
    """
    if not isinstance(app_config, dict):
        raise ValidationError(
            "app_config must be a dict, got " f"{type(app_config).__name__}"
        )
    pc = app_config.get("provider_clients")
    if pc is None:
        raise ValidationError("app_config.provider_clients section is required")
    if provider_name is None or (provider_name or "").strip() == "":
        return get_default_client(pc, validate=validate)
    return get_client(provider_name, pc, validate=validate)


def list_supported_providers() -> tuple[str, ...]:
    """
    Return provider names for which a client builder is registered.

    Used by callers to know which provider names are valid for get_client.
    """
    return tuple(sorted(_PROVIDER_BUILDERS.keys()))
