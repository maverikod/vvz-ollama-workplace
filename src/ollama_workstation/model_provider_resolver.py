"""
Resolve model_id to provider, base URL, and API key. URL bound to model type.

Provider URLs from config.provider_urls; fallback to defaults.
Used by chat_flow and direct_chat to route requests to correct backend.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, TYPE_CHECKING

from .docker_config_validation import get_provider_for_model
from .provider_errors import ValidationError

if TYPE_CHECKING:
    from .config import WorkstationConfig


# Default base URLs per provider (OpenAI-compatible or OpenRouter).
DEFAULT_PROVIDER_URLS: Dict[str, str] = {
    "ollama": "http://127.0.0.1:11434",
    "openrouter": "https://openrouter.ai/api/v1",
    "openai": "https://api.openai.com/v1",
    "xai": "https://api.x.ai/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "google": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "anthropic": "https://api.anthropic.com/v1",
}

# OpenRouter model id format: provider/model-name.
OPENROUTER_MODEL_PREFIX: Dict[str, str] = {
    "google": "google",
    "anthropic": "anthropic",
    "openai": "openai",
    "xai": "x-ai",
    "deepseek": "deepseek",
}


@dataclass
class ModelEndpoint:
    """Resolved endpoint for a model: URL, API key, and format."""

    base_url: str
    api_key: Optional[str]
    provider: str
    model_id: str  # May differ for OpenRouter (e.g. google/gemini-2.0-flash).
    is_ollama: bool  # True => POST /api/chat; False => POST /v1/chat/completions.


def _get_provider_from_config(
    config: "WorkstationConfig", provider: str
) -> tuple[str, Optional[str]]:
    """
    Get (url, api_key) for provider from model_providers or legacy keys.
    Returns (url, api_key); url may be empty if not configured.
    """
    mp = getattr(config, "model_providers", None) or {}
    prov_cfg = mp.get(provider) if isinstance(mp, dict) else {}
    url = ""
    key: Optional[str] = None
    if isinstance(prov_cfg, dict):
        url = (prov_cfg.get("url") or "").strip().rstrip("/")
        key = (prov_cfg.get("api_key") or "").strip() or None
    if not url:
        urls = getattr(config, "provider_urls", None) or {}
        url = (urls.get(provider) or "").strip().rstrip("/")
    if not key:
        key_map = {
            "google": config.google_api_key,
            "anthropic": config.anthropic_api_key,
            "openai": config.openai_api_key,
            "xai": config.xai_api_key,
            "deepseek": config.deepseek_api_key,
        }
        key = key_map.get(provider)
    return url, key


def _get_api_key_for_provider(
    config: "WorkstationConfig", provider: str
) -> Optional[str]:
    """Return API key for provider from config."""
    key_map = {
        "google": config.google_api_key,
        "anthropic": config.anthropic_api_key,
        "openai": config.openai_api_key,
        "xai": config.xai_api_key,
        "deepseek": config.deepseek_api_key,
    }
    return key_map.get(provider)


def _openrouter_model_id(provider: str, model_id: str) -> str:
    """Convert model_id to OpenRouter format (provider/model-name)."""
    prefix = OPENROUTER_MODEL_PREFIX.get(provider, provider)
    if "/" in model_id:
        return model_id
    return "%s/%s" % (prefix, model_id)


def resolve_model_endpoint(
    model_id: str,
    config: "WorkstationConfig",
    provider_urls: Optional[Dict[str, str]] = None,
    openrouter_api_key: Optional[str] = None,
) -> ModelEndpoint:
    """
    Resolve model_id to endpoint (URL, key, format).

    URL is bound to model type (provider). Uses provider_urls from config
    or passed dict; fallback to DEFAULT_PROVIDER_URLS.

    When openrouter URL is configured and openrouter_api_key is set,
    commercial models are routed through OpenRouter. Otherwise direct
    provider URLs are used (requires provider-specific API keys).

    Args:
        model_id: Model identifier (e.g. llama3.2, gemini-2.0-flash).
        config: Workstation config (for keys and ollama URL).
        provider_urls: Optional override for provider -> base_url.
        openrouter_api_key: Optional OpenRouter key (env or config).

    Returns:
        ModelEndpoint with base_url, api_key, provider, model_id, is_ollama.
    """
    if not model_id or not isinstance(model_id, str):
        model_id = (config.ollama_model or "").strip() or "llama3.2"
    model_id = model_id.strip()
    provider = get_provider_for_model(model_id)

    # Ollama: url and optional api_key from model_providers or legacy.
    if provider == "ollama":
        url, key = _get_provider_from_config(config, "ollama")
        base = url or (
            (config.model_server_url or config.ollama_base_url) or ""
        ).rstrip("/")
        if not base:
            base = DEFAULT_PROVIDER_URLS.get("ollama", "http://127.0.0.1:11434")
        return ModelEndpoint(
            base_url=base,
            api_key=key or config.ollama_api_key,
            provider="ollama",
            model_id=model_id,
            is_ollama=True,
        )

    # Commercial: use direct provider when it has url and api_key.
    url, key = _get_provider_from_config(config, provider)
    direct_url: str = (url or "").strip().rstrip("/") or (
        DEFAULT_PROVIDER_URLS.get(provider) or ""
    )
    api_key = (key or _get_api_key_for_provider(config, provider)) or None
    if api_key is not None:
        api_key = str(api_key).strip() or None
    if direct_url and api_key:
        return ModelEndpoint(
            base_url=direct_url,
            api_key=api_key,
            provider=provider,
            model_id=model_id,
            is_ollama=False,
        )

    # OpenRouter only when direct provider is not fully configured.
    openrouter_url, openrouter_key = _get_provider_from_config(config, "openrouter")
    openrouter_url = (openrouter_url or "").strip().rstrip("/") or (
        DEFAULT_PROVIDER_URLS.get("openrouter") or ""
    )
    openrouter_key = (
        openrouter_api_key
        if openrouter_api_key is not None
        else getattr(config, "openrouter_api_key", None) or openrouter_key
    )
    if openrouter_url and openrouter_key and str(openrouter_key).strip():
        return ModelEndpoint(
            base_url=openrouter_url,
            api_key=openrouter_key.strip(),
            provider="openrouter",
            model_id=_openrouter_model_id(provider, model_id),
            is_ollama=False,
        )

    # No key: still return direct URL so caller gets a clear error.
    return ModelEndpoint(
        base_url=direct_url or "https://api.openai.com/v1",
        api_key=api_key,
        provider=provider,
        model_id=model_id,
        is_ollama=False,
    )


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
    is_ollama = provider == "ollama"
    return ModelEndpoint(
        base_url=base_url,
        api_key=api_key,
        provider=provider,
        model_id=use_model,
        is_ollama=is_ollama,
    )
