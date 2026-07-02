# STEP-I1 — OpenAIProviderClient (new file)

**File:** `src/mwps/openai_provider_client.py` (new)
**Provider:** `openai` — also base for xAI, DeepSeek
**Severity:** 🔴 High
**Depends on:** STEP-08 (BaseProviderClient is proper ABC)
**Blocks:** STEP-I4, STEP-I5, STEP-S1 (embed used in search)

---

## API endpoints

| Operation | Endpoint | Notes |
|-----------|----------|-------|
| chat | `POST {base_url}/v1/chat/completions` | stream or not |
| embed | `POST {base_url}/v1/embeddings` | returns `data[0].embedding` |
| models | `GET {base_url}/v1/models` | for healthcheck |

## Request/response shapes

### chat request
```json
{
  "model": "gpt-4o",
  "messages": [...],
  "tools": [...],
  "stream": false,
  "max_tokens": 4096
}
```

### embed request
```json
{"model": "text-embedding-3-small", "input": "query text"}
```
Response: `{"data": [{"embedding": [0.1, 0.2, ...]}]}`

## Task

```python
class OpenAICompatibleProviderClient(BaseProviderClient):
    """Base for OpenAI-compatible REST APIs.
    Parameterised by base_url, api_key, model, embed_model, timeout.
    Subclass and override only what differs (e.g. extra headers).
    """

    def __init__(self, config: ProviderSectionConfig) -> None: ...

    @property
    def supports_stream(self) -> bool: return True
    @property
    def supports_tools(self) -> bool: return True
    @property
    def supports_embeddings(self) -> bool:
        return bool(self._embed_model)

    def validate_config(self) -> None:
        """Check base_url non-empty, api_key non-empty."""

    def healthcheck(self) -> bool:
        """GET /v1/models, expect 200."""

    async def chat(self, request: Any) -> Any:
        """POST /v1/chat/completions.
        request is already serialized (list of messages in OpenAI format).
        Returns raw response dict.
        """

    async def embed(self, request: Any) -> Any:
        """POST /v1/embeddings.
        request: str or list[str].
        Returns list of embedding vectors.
        Raises CapabilityNotSupportedError if embed_model not set.
        """

    def normalize_response(self, raw: Any) -> Any:
        """Extract message from choices[0].message."""

    def map_error(self, exc: BaseException) -> ProviderError:
        """Map httpx errors to ProviderError subclasses."""


class OpenAIProviderClient(OpenAICompatibleProviderClient):
    """OpenAI provider. Uses Authorization: Bearer {api_key}."""
```

## Acceptance criteria

- [ ] `chat()` sends correct headers (`Authorization: Bearer {api_key}`)
- [ ] `embed()` raises `CapabilityNotSupportedError` when embed_model not set
- [ ] `normalize_response()` returns `{"message": {"role": ..., "content": ..., "tool_calls": ...}}`
- [ ] `map_error()` maps: 401 → AuthError, 429 → RateLimitError, timeout → TimeoutError, network → TransportError
- [ ] `validate_config()` raises `ValidationError` for empty `base_url` or `api_key`
- [ ] `healthcheck()` returns `True` on 200, `False` on connection error (does not raise)
- [ ] Configurable timeout from `config.limits.request_timeout_seconds`
- [ ] Unit tests with httpx mock
- [ ] `lint_code` + `type_check_code` pass
