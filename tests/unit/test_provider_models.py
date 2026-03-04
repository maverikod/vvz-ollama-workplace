"""
Unit tests for provider_models: cheapest model per provider.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from ollama_workstation.provider_models import (  # noqa: E402
    CHEAPEST_MODEL_BY_PROVIDER,
    get_cheapest_model,
)


def test_cheapest_model_by_provider_has_all_providers() -> None:
    """Google, Anthropic, OpenAI, xAI, DeepSeek have a cheapest model id."""
    assert CHEAPEST_MODEL_BY_PROVIDER["google"].startswith("gemini")
    assert "haiku" in CHEAPEST_MODEL_BY_PROVIDER["anthropic"].lower()
    assert "gpt" in CHEAPEST_MODEL_BY_PROVIDER["openai"].lower()
    assert "grok" in CHEAPEST_MODEL_BY_PROVIDER["xai"].lower()
    assert "deepseek" in CHEAPEST_MODEL_BY_PROVIDER["deepseek"].lower()


def test_get_cheapest_model() -> None:
    """get_cheapest_model returns id for known provider, None otherwise."""
    assert get_cheapest_model("google") == "gemini-2.0-flash"
    assert get_cheapest_model("Google") == "gemini-2.0-flash"
    assert get_cheapest_model("anthropic") == "claude-3-5-haiku-20241022"
    assert get_cheapest_model("openai") == "gpt-4o-mini"
    assert get_cheapest_model("xai") == "grok-2"
    assert get_cheapest_model("grok") == "grok-2"
    assert get_cheapest_model("deepseek") == "deepseek-chat"
    assert get_cheapest_model("ollama") is None
    assert get_cheapest_model("") is None
    assert get_cheapest_model("unknown") is None
