"""
Resolve model_id to provider, base URL, and API key. URL bound to model type.

Canonical source is provider_clients (see resolve_model_endpoint_from_provider_clients).
Direct commercial provider routing was removed; commercial LLM access is
delegated to model-access-core (separate reorientation step).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from .docker_config_validation import get_provider_for_model
from .provider_errors import ValidationError


@dataclass
class ModelEndpoint:
    """Resolved endpoint for a model: URL, API key, and format."""

    base_url: str
    api_key: Optional[str]
    provider: str
    model_id: str  # May differ for OpenRouter (e.g. google/gemini-2.0-flash).
    is_mwps: bool  # True => POST /api/chat; False => POST /v1/chat/completions.


def _auth_credential_from_section(section: Any) -> Optional[str]:
    """Extract api_key or bearer_token from provider section auth."""
    auth = section.get("auth") if isinstance(section, dict) else None
    if not isinstance(auth, dict):
        return None
    for key in ("api_key", "bearer_token"):
        val = auth.get(key)
        if val and isinstance(val, str) and val.strip():
            return str(val.strip())
    return None


def resolve_model_endpoint_from_provider_clients(
    provider_clients_data: Any,
    model_id: str,
    default_model: str = "llama3.2",
) -> ModelEndpoint:
    """
    Resolve model_id to ModelEndpoint using only provider_clients (canonical source).

    Used by model-workspace runtime; no legacy model_providers or flat api_key.
    Raises ValidationError if provider is not in provider_clients.providers.
    """
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
    use_model = (model_id or "").strip() or default_model
    provider = get_provider_for_model(use_model)
    if provider not in providers:
        raise ValidationError(
            f"provider '{provider}' (for model {use_model!r}) not in "
            f"provider_clients.providers; available: {sorted(providers.keys())}"
        )
    section = providers[provider]
    if not isinstance(section, dict):
        raise ValidationError(
            f"provider_clients.providers.{provider} must be an object"
        )
    transport = section.get("transport") or {}
    base_url = (transport.get("base_url") or "").strip().rstrip("/")
    if not base_url:
        raise ValidationError(
            f"provider_clients.providers.{provider}.transport.base_url is required"
        )
    api_key = _auth_credential_from_section(section)
    is_mwps = provider == "mwps"
    return ModelEndpoint(
        base_url=base_url,
        api_key=api_key,
        provider=provider,
        model_id=use_model,
        is_mwps=is_mwps,
    )
