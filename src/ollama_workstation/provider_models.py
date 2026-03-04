"""
Cheapest (lowest-cost) model id per commercial provider for defaults and docs.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

# Cheapest model id per provider (API name). Use for default/example config.
# Google: Gemini 2.0 Flash is the low-cost option; Flash-Lite is even cheaper.
# Anthropic: Claude 3.5 Haiku is the cheapest tier.
# OpenAI: GPT-4o mini is the most cost-efficient.
# xAI: Grok 2; DeepSeek: deepseek-chat.
CHEAPEST_MODEL_BY_PROVIDER: dict[str, str] = {
    "google": "gemini-2.0-flash",
    "anthropic": "claude-3-5-haiku-20241022",
    "openai": "gpt-4o-mini",
    "xai": "grok-2",
    "grok": "grok-2",
    "deepseek": "deepseek-chat",
}


def get_cheapest_model(provider: str) -> str | None:
    """Return the cheapest model id for the provider, or None if unknown."""
    if not provider or not isinstance(provider, str):
        return None
    return CHEAPEST_MODEL_BY_PROVIDER.get(provider.strip().lower())
