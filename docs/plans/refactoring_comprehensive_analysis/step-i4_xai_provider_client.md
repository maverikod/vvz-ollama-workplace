# STEP-I4 — XAIProviderClient + STEP-I5 DeepSeekProviderClient

**Files:** `xai_provider_client.py`, `deepseek_provider_client.py` (new)
**Providers:** `xai`, `deepseek` — both OpenAI-compatible
**Severity:** 🔴 High
**Depends on:** STEP-I1 (OpenAICompatibleProviderClient base)

---

## xAI (Grok)

| Param | Value |
|-------|-------|
| Base URL | `https://api.x.ai` |
| Chat | `/v1/chat/completions` (OpenAI-compatible) |
| Embed | **Not supported** |
| Auth | `Authorization: Bearer {api_key}` |
| Default model | `grok-3` |

```python
class XAIProviderClient(OpenAICompatibleProviderClient):
    """xAI Grok provider. OpenAI-compatible, no embeddings."""

    @property
    def supports_embeddings(self) -> bool:
        return False   # override: xAI has no embed endpoint

    async def embed(self, request) -> Any:
        raise CapabilityNotSupportedError("xAI does not support embeddings")
```

---

## DeepSeek

| Param | Value |
|-------|-------|
| Base URL | `https://api.deepseek.com` |
| Chat | `/v1/chat/completions` (OpenAI-compatible) |
| Embed | **Not supported** |
| Auth | `Authorization: Bearer {api_key}` |
| Default model | `deepseek-chat` |
| Note | DeepSeek uses `reasoning_content` field for chain-of-thought; `normalize_response` must handle it |

```python
class DeepSeekProviderClient(OpenAICompatibleProviderClient):
    """DeepSeek provider. OpenAI-compatible with reasoning_content extension."""

    @property
    def supports_embeddings(self) -> bool:
        return False

    async def embed(self, request) -> Any:
        raise CapabilityNotSupportedError("DeepSeek does not support embeddings")

    def normalize_response(self, raw) -> Any:
        """Extends parent: also extracts reasoning_content if present."""
        result = super().normalize_response(raw)
        reasoning = raw.get("choices", [{}])[0].get(
            "message", {}
        ).get("reasoning_content")
        if reasoning:
            result["message"]["reasoning"] = reasoning
        return result
```

## Acceptance criteria

- [ ] Both classes inherit `OpenAICompatibleProviderClient`
- [ ] Both: `embed()` raises `CapabilityNotSupportedError`
- [ ] DeepSeek: `normalize_response()` extracts `reasoning_content` when present
- [ ] Both: `validate_config()` inherited, checks api_key
- [ ] Unit tests
- [ ] `lint_code` + `type_check_code` pass
