"""
Validator for provider_clients configuration section.

Enforces config standard rules V1–V11: structure, default_provider present in
providers, auth and TLS consistency with protocol/endpoint. Rejects incomplete
or conflicting settings before runtime. Invokable at startup or via CLI; raises
ValidationError or returns list of (path, message) for integration.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from typing import Any

from ollama_workstation.provider_client_config_schema import (
    validate_provider_clients_structure,
)
from ollama_workstation.provider_errors import ValidationError

# Providers that require auth (API key or bearer) when used as active provider.
# Config standard §3.2: auth required when protocol requires it.
_PROVIDERS_REQUIRING_AUTH = frozenset(
    {"openai", "anthropic", "google", "xai", "deepseek"}
)


def _base_url_scheme(transport: Any) -> str | None:
    """Return URL scheme (e.g. 'https', 'http') from transport.base_url or None."""
    if not isinstance(transport, dict):
        return None
    base_url = transport.get("base_url")
    if not base_url or not isinstance(base_url, str):
        return None
    url = (base_url or "").strip()
    if not url:
        return None
    if url.startswith("https://") or url.startswith("wss://"):
        return "secure"
    if url.startswith("http://") or url.startswith("ws://"):
        return "insecure"
    return None


def _active_provider_requires_auth(provider_name: str) -> bool:
    """True if this provider name typically requires auth (API key/bearer)."""
    return provider_name.strip().lower() in _PROVIDERS_REQUIRING_AUTH


def _auth_has_credentials(auth: Any) -> bool:
    """True if auth section has at least one credential (api_key or bearer_token)."""
    if not isinstance(auth, dict):
        return False
    api_key = auth.get("api_key")
    bearer = auth.get("bearer_token")
    return bool(
        (api_key and isinstance(api_key, str) and api_key.strip())
        or (bearer and isinstance(bearer, str) and bearer.strip())
    )


def _validate_active_provider_auth_tls(
    provider_name: str,
    section: Any,
    path_prefix: str,
    errors: list[tuple[str, str]],
) -> None:
    """
    Enforce V6–V11 for the active provider: auth and TLS vs protocol/endpoint.
    Appends to errors; does not raise.
    """
    if not isinstance(section, dict):
        return
    transport = section.get("transport")
    auth = section.get("auth")
    tls = section.get("tls")

    # V8/V9/V10/V11: TLS vs endpoint
    scheme = _base_url_scheme(transport) if transport else None
    if scheme == "secure":
        if not tls or not isinstance(tls, dict):
            errors.append(
                (
                    f"{path_prefix}.tls",
                    "TLS section is required when base_url uses https:// or wss://",
                )
            )
        elif tls.get("verify") is False:
            errors.append(
                (
                    f"{path_prefix}.tls",
                    "inconsistent: endpoint is secure but tls.verify is false",
                )
            )

    # V6/V7/V10: Auth when required
    if _active_provider_requires_auth(provider_name):
        if not auth or not isinstance(auth, dict):
            errors.append(
                (
                    f"{path_prefix}.auth",
                    "auth with api_key or bearer_token is required for this provider",
                )
            )
        elif not _auth_has_credentials(auth):
            errors.append(
                (
                    f"{path_prefix}.auth",
                    "api_key or bearer_token must be non-empty for this provider",
                )
            )


def validate_provider_clients(provider_clients_data: Any) -> list[tuple[str, str]]:
    """
    Validate provider_clients section (structure + auth/TLS vs protocol).

    Implements config standard V1–V11. Returns list of (field_path, message).
    Empty list means valid. Use validate_provider_clients_or_raise to fail fast.
    """
    errors = validate_provider_clients_structure(
        provider_clients_data,
        reject_unknown_provider_keys=True,
    )
    if errors:
        return errors

    # V4: default_provider must exist under providers
    data = provider_clients_data
    default_provider = (data.get("default_provider") or "").strip()
    providers = data.get("providers")
    if not default_provider or not isinstance(providers, dict):
        return errors
    if default_provider not in providers:
        errors.append(
            (
                "provider_clients.default_provider",
                f"provider '{default_provider}' not in providers",
            )
        )
        return errors

    # V5/V6–V11: active provider section auth and TLS
    active_section = providers.get(default_provider)
    path_prefix = f"provider_clients.providers.{default_provider}"
    _validate_active_provider_auth_tls(
        default_provider,
        active_section,
        path_prefix,
        errors,
    )
    # Runtime-allowed commercial providers: each must have base_url and auth.
    for prov_name, section in providers.items():
        if not isinstance(prov_name, str) or not isinstance(section, dict):
            continue
        pprefix = f"provider_clients.providers.{prov_name}"
        transport = section.get("transport")
        base_url = (
            (transport.get("base_url") or "").strip()
            if isinstance(transport, dict)
            else ""
        )
        if not base_url:
            errors.append(
                (f"{pprefix}.transport.base_url", "is required for every provider")
            )
        _validate_active_provider_auth_tls(prov_name, section, pprefix, errors)
    return errors


def validate_provider_clients_or_raise(provider_clients_data: Any) -> None:
    """
    Validate provider_clients section; raise ValidationError on first failure.

    For startup integration: call before using config. Message includes all
    (path, message) pairs for diagnostics.
    """
    errors = validate_provider_clients(provider_clients_data)
    if not errors:
        return
    msg = "; ".join(f"{path}: {m}" for path, m in errors)
    raise ValidationError(msg)


def validate_config_provider_clients(app_config: Any) -> list[tuple[str, str]]:
    """
    Extract provider_clients from full app config and validate.

    If provider_clients key is missing, returns single error (so caller can
    fail fast or report). Use for workstation startup: pass loaded config dict.
    """
    if not isinstance(app_config, dict):
        return [("config", "must be an object")]
    pc = app_config.get("provider_clients")
    if pc is None:
        return [("provider_clients", "section is required")]
    return validate_provider_clients(pc)
