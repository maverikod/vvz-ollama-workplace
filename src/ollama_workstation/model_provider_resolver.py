"""
Resolve model_id to provider, base URL, and API key. URL bound to model type.

Provider URLs from config.provider_urls; fallback to defaults.
Used by chat_flow and direct_chat to route requests to correct backend.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, TYPE_CHECKING

from .docker_config_validation import get_provider_for_model

if TYPE_CHECKING:
    from .config import WorkstationConfig


# Default base URLs per provider (OpenAI-compatible or OpenRouter).
DEFAULT_PROVIDER_URLS: Dict[str, str] = {
    "ollama": "http://127.0.0.1:11434",
    "openrouter": "https://openrouter.ai/api/v1",
    "openai": "https://api.openai.com/v1",
    "xai": "https://api.x.ai/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "google": "https://generativelanguage.googleapis.com/v1beta",
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

    # Commercial: url and api_key from model_providers (mandatory when model selected).
    url, key = _get_provider_from_config(config, provider)

    # Optional: OpenRouter as fallback when configured.
    openrouter_url, openrouter_key = _get_provider_from_config(config, "openrouter")
    if not openrouter_url:
        openrouter_url = DEFAULT_PROVIDER_URLS.get("openrouter") or ""
    openrouter_key = (
        openrouter_api_key
        if openrouter_api_key is not None
        else getattr(config, "openrouter_api_key", None) or openrouter_key
    )
    if openrouter_url and openrouter_key and str(openrouter_key).strip():
        return ModelEndpoint(
            base_url=openrouter_url.rstrip("/"),
            api_key=openrouter_key,
            provider="openrouter",
            model_id=_openrouter_model_id(provider, model_id),
            is_ollama=False,
        )

    # Direct provider: url and key from model_providers.
    direct_url: str = url or (DEFAULT_PROVIDER_URLS.get(provider) or "")
    if not direct_url:
        direct_url = DEFAULT_PROVIDER_URLS.get("openai") or "https://api.openai.com/v1"
    return ModelEndpoint(
        base_url=direct_url.rstrip("/"),
        api_key=key or _get_api_key_for_provider(config, provider),
        provider=provider,
        model_id=model_id,
        is_ollama=False,
    )
