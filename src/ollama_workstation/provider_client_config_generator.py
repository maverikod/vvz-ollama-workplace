"""
Generate provider_clients configuration section.

Produces a valid provider_clients section (or full config including it) that
conforms to the config standard and schema. Output is suitable for the
provider client config validator (step_06). Supports template/example
generation (e.g. default ollama provider with transport/auth/tls/features/limits).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from typing import Any

from ollama_workstation.provider_client_config_schema import (
    get_empty_provider_clients_section,
    get_empty_provider_section,
)
from ollama_workstation.provider_client_config_validator import (
    validate_provider_clients,
)


def get_default_ollama_provider_section(
    *,
    base_url: str = "http://localhost:11434",
    connect_timeout_seconds: int = 30,
    request_timeout_seconds: int = 120,
    retry_max_attempts: int = 3,
    supports_stream: bool = True,
    supports_tools: bool = False,
    supports_embeddings: bool = True,
    max_tokens: int | None = None,
    timeout_seconds: int | None = None,
) -> dict[str, Any]:
    """
    Return a valid provider section for the ollama provider.

    Fills transport (required), optional auth, tls, features, limits per
    config standard. TLS/auth left empty for typical local HTTP ollama.
    """
    section = get_empty_provider_section()
    section["transport"] = {
        "base_url": base_url,
        "protocol": "http",
        "connect_timeout_seconds": connect_timeout_seconds,
        "request_timeout_seconds": request_timeout_seconds,
        "retry_max_attempts": retry_max_attempts,
    }
    section["auth"] = {}
    section["tls"] = {}
    section["features"] = {
        "supports_stream": supports_stream,
        "supports_tools": supports_tools,
        "supports_embeddings": supports_embeddings,
    }
    limits: dict[str, Any] = {}
    if max_tokens is not None:
        limits["max_tokens"] = max_tokens
    if timeout_seconds is not None:
        limits["timeout_seconds"] = timeout_seconds
    section["limits"] = limits
    return section


def generate_provider_clients_section(
    default_provider: str = "ollama",
    providers: dict[str, dict[str, Any]] | None = None,
    *,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Generate a valid provider_clients section.

    If providers is None, uses a single default ollama provider so that
    default_provider exists in providers. If providers is given, it must
    contain default_provider. When validate is True, runs structure
    validation and raises ValueError if invalid.
    """
    if providers is None:
        providers = {
            "ollama": get_default_ollama_provider_section(),
        }
    if default_provider not in providers:
        raise ValueError(
            f"default_provider '{default_provider}' must exist in providers; "
            f"got keys: {sorted(providers.keys())}"
        )
    out = get_empty_provider_clients_section()
    out["default_provider"] = default_provider
    out["providers"] = dict(providers)

    if validate:
        errors = validate_provider_clients(out)
        if errors:
            msg = "; ".join(f"{path}: {m}" for path, m in errors)
            raise ValueError(f"Generated config failed validation: {msg}")
    return out


def generate_full_config_with_provider_clients(
    provider_clients_section: dict[str, Any],
    top_level_keys: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build a full config dict that includes the given provider_clients section.

    Other top-level keys can be passed in top_level_keys; provider_clients
    will override any key named "provider_clients" there.
    """
    full: dict[str, Any] = dict(top_level_keys) if top_level_keys else {}
    full["provider_clients"] = provider_clients_section
    return full


def generate_sample(
    default_provider: str = "ollama",
    *,
    full_config: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Generate a sample provider_clients section (or full config) with one provider.

    Uses default ollama template. When full_config is True, returns a dict
    with a single key "provider_clients" containing the section (suitable
    for merging into a larger config). When full_config is False, returns
    only the provider_clients section dict.
    """
    section = generate_provider_clients_section(
        default_provider=default_provider,
        providers=None,
        validate=validate,
    )
    if full_config:
        return generate_full_config_with_provider_clients(section)
    return section
