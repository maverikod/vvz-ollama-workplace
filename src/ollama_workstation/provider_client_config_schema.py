"""
Schema for provider_clients configuration section.

Defines allowed structure, keys, and types for provider_clients (default_provider,
providers.<name>.transport, .auth, .tls, .features, .limits). Usable by the
config validator (step_06) and config generator (step_07). Aligned with
docs/standards/provider_client_config_standard.md.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import re
from typing import Any

# --- Top-level provider_clients keys -----------------------------------------

PROVIDER_CLIENTS_TOP_LEVEL_KEYS = frozenset({"default_provider", "providers"})

# --- Per-provider section keys (under providers.<name>) ----------------------

PROVIDER_SECTION_KEYS = frozenset({"transport", "auth", "tls", "features", "limits"})

# Required per-provider key (config standard §1.2)
REQUIRED_PROVIDER_SECTION_KEYS = frozenset({"transport"})

# --- Allowed keys inside each subsection (reject unknown keys) -----------------
# Normative: config standard §1.2 describes content; schema restricts to known keys.

# Transport: base URL, protocol type, timeouts
ALLOWED_TRANSPORT_KEYS = frozenset(
    {
        "base_url",
        "protocol",
        "connect_timeout_seconds",
        "request_timeout_seconds",
        "retry_max_attempts",
    }
)

# Auth: API key, bearer token, client cert paths
ALLOWED_AUTH_KEYS = frozenset(
    {
        "api_key",
        "bearer_token",
        "client_cert_file",
        "client_key_file",
    }
)

# TLS: verify, client cert, CA
ALLOWED_TLS_KEYS = frozenset(
    {
        "verify",
        "client_cert_file",
        "client_key_file",
        "ca_cert_file",
    }
)

# Features: supports_stream, supports_tools, model-specific caps
ALLOWED_FEATURES_KEYS = frozenset(
    {
        "supports_stream",
        "supports_tools",
        "supports_embeddings",
    }
)

# Limits: max_tokens, timeout_seconds, rate limits
ALLOWED_LIMITS_KEYS = frozenset(
    {
        "max_tokens",
        "timeout_seconds",
        "rate_limit_rpm",
        "rate_limit_tpm",
    }
)

# --- Canonical provider names (config standard §2) ----------------------------

CANONICAL_PROVIDER_NAMES = frozenset(
    {
        "ollama",
        "openai",
        "anthropic",
        "google",
        "xai",
        "deepseek",
    }
)

# Provider name pattern: lowercase, hyphen-free (config standard §2)
PROVIDER_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def is_valid_provider_name(name: str) -> bool:
    """
    Return True if provider name is allowed (canonical or matches naming rule).

    Canonical names are always valid. Other names are valid if lowercase and
    hyphen-free (alphanumeric + underscore).
    """
    if not name or not isinstance(name, str):
        return False
    s = name.strip()
    if s in CANONICAL_PROVIDER_NAMES:
        return True
    return bool(PROVIDER_NAME_PATTERN.match(s))


def _check_object(
    value: Any,
    allowed_keys: frozenset[str],
    path: str,
    errors: list[tuple[str, str]],
    *,
    allow_extra: bool = False,
) -> bool:
    """Append errors if not a dict or has disallowed keys. Return True if ok."""
    if not isinstance(value, dict):
        errors.append((path, "must be an object"))
        return False
    if allow_extra:
        return True
    for key in value:
        if key not in allowed_keys:
            allowed = sorted(allowed_keys)
            errors.append((f"{path}.{key}", f"disallowed key; allowed: {allowed}"))
    return len(errors) == 0 or not any(e[0].startswith(path) for e in errors)


def validate_provider_clients_structure(
    data: Any,
    *,
    reject_unknown_provider_keys: bool = True,
) -> list[tuple[str, str]]:
    """
    Validate structure and types of provider_clients section only.

    Does not enforce V4–V11 (default_provider present in providers, auth/TLS
    vs protocol); the validator (step_06) uses this for structure and adds
    protocol/auth/TLS rules.

    Returns list of (field_path, message). Empty list means structure is valid.
    """
    errors: list[tuple[str, str]] = []
    prefix = "provider_clients"

    if not isinstance(data, dict):
        errors.append((prefix, "must be an object"))
        return errors

    for key in data:
        if key not in PROVIDER_CLIENTS_TOP_LEVEL_KEYS:
            allowed_top = sorted(PROVIDER_CLIENTS_TOP_LEVEL_KEYS)
            errors.append(
                (f"{prefix}.{key}", f"disallowed key; allowed: {allowed_top}")
            )

    # default_provider: required, non-empty string
    default_provider = data.get("default_provider")
    if default_provider is None:
        errors.append((f"{prefix}.default_provider", "is required"))
    elif not isinstance(default_provider, str):
        errors.append((f"{prefix}.default_provider", "must be a string"))
    elif not default_provider.strip():
        errors.append((f"{prefix}.default_provider", "must be non-empty"))

    # providers: required, object, at least one entry
    providers = data.get("providers")
    if providers is None:
        errors.append((f"{prefix}.providers", "is required"))
    elif not isinstance(providers, dict):
        errors.append((f"{prefix}.providers", "must be an object"))
    else:
        if len(providers) == 0:
            errors.append((f"{prefix}.providers", "must have at least one provider"))
        for prov_name, prov_section in providers.items():
            if not isinstance(prov_name, str):
                errors.append(
                    (
                        f"{prefix}.providers",
                        f"provider name must be string, got {type(prov_name).__name__}",
                    )
                )
                continue
            if not is_valid_provider_name(prov_name):
                errors.append(
                    (
                        f"{prefix}.providers.{prov_name}",
                        "invalid provider name (use lowercase, hyphen-free)",
                    )
                )
            _validate_provider_section(
                prov_section,
                f"{prefix}.providers.{prov_name}",
                errors,
                reject_unknown_keys=reject_unknown_provider_keys,
            )

    return errors


def _validate_provider_section(
    section: Any,
    path: str,
    errors: list[tuple[str, str]],
    *,
    reject_unknown_keys: bool = True,
) -> None:
    """Validate one provider section: transport, auth, tls, features, limits."""
    if not isinstance(section, dict):
        errors.append((path, "must be an object"))
        return

    for key in section:
        if key not in PROVIDER_SECTION_KEYS:
            allowed_sec = sorted(PROVIDER_SECTION_KEYS)
            errors.append((f"{path}.{key}", f"disallowed key; allowed: {allowed_sec}"))

    # transport: required object
    transport = section.get("transport")
    if transport is None:
        errors.append((f"{path}.transport", "is required"))
    else:
        _check_object(
            transport,
            ALLOWED_TRANSPORT_KEYS,
            f"{path}.transport",
            errors,
            allow_extra=not reject_unknown_keys,
        )

    # auth: optional object
    auth = section.get("auth")
    if auth is not None:
        _check_object(
            auth,
            ALLOWED_AUTH_KEYS,
            f"{path}.auth",
            errors,
            allow_extra=not reject_unknown_keys,
        )

    # tls: optional object
    tls = section.get("tls")
    if tls is not None:
        _check_object(
            tls,
            ALLOWED_TLS_KEYS,
            f"{path}.tls",
            errors,
            allow_extra=not reject_unknown_keys,
        )

    # features: optional object
    features = section.get("features")
    if features is not None:
        _check_object(
            features,
            ALLOWED_FEATURES_KEYS,
            f"{path}.features",
            errors,
            allow_extra=not reject_unknown_keys,
        )

    # limits: optional object
    limits = section.get("limits")
    if limits is not None:
        _check_object(
            limits,
            ALLOWED_LIMITS_KEYS,
            f"{path}.limits",
            errors,
            allow_extra=not reject_unknown_keys,
        )


def get_empty_provider_section() -> dict[str, Any]:
    """
    Return a minimal valid provider section structure (transport only, empty).

    Generator (step_07) can use this as template and fill required fields.
    """
    return {
        "transport": {},
        "auth": {},
        "tls": {},
        "features": {},
        "limits": {},
    }


def get_empty_provider_clients_section() -> dict[str, Any]:
    """
    Return minimal valid provider_clients structure (no providers).

    Generator can set default_provider and add providers to this.
    """
    return {
        "default_provider": "",
        "providers": {},
    }
