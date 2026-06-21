# STEP-I2 — AnthropicProviderClient (new file)

**File:** `src/ollama_workstation/anthropic_provider_client.py` (new)
**Provider:** `anthropic`
**Severity:** 🔴 High
**Depends on:** STEP-08

---

## API specifics

| Param | Value |
|-------|-------|
| Base URL | `https://api.anthropic.com` |
| Chat endpoint | `POST /v1/messages` |
| Embed | **Not supported** (`supports_embeddings = False`) |
| Required headers | `x-api-key: {api_key}`, `anthropic-version: {version}`, `content-type: application/json` |

## Chat request shape

```json
{
  "model": "claude-opus-4-6",
  "max_tokens": 4096,
  "system": "You are...",
  "messages": [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": [
      {"type": "tool_use", "id": "toolu_01", "name": "...", "input": {...}}
    ]},
    {"role": "user", "content": [
      {"type": "tool_result", "tool_use_id": "toolu_01", "content": "..."}
    ]}
  ],
  "tools": [{"name": "...", "description": "...", "input_schema": {...}}]
}
```

Note: `system` is a **top-level string**, not a message.
`AnthropicRepresentation.get_system_prompt()` extracts it.

## Response normalization

Anthropic returns:
```json
{
  "content": [
    {"type": "text", "text": "..."},
    {"type": "tool_use", "id": "...", "name": "...", "input": {...}}
  ],
  "stop_reason": "tool_use" | "end_turn"
}
```
`normalize_response()` converts to workstation-internal format:
```python
{
    "message": {
        "role": "assistant",
        "content": "<text content or None>",
        "tool_calls": [  # only when stop_reason == "tool_use"
            {"id": "...", "name": "...", "arguments": {...}}
        ]
    },
    "finish_reason": "tool_use" | "stop"
}
```

## Task

```python
class AnthropicProviderClient(BaseProviderClient):
    """Anthropic Messages API client."""

    @property
    def supports_stream(self) -> bool: return True
    @property
    def supports_tools(self) -> bool: return True
    @property
    def supports_embeddings(self) -> bool: return False

    def validate_config(self) -> None:
        """Check api_key and anthropic_version non-empty."""

    def healthcheck(self) -> bool:
        """Lightweight call — GET /v1/models or POST with min tokens."""

    async def chat(self, request) -> Any:
        """POST /v1/messages. Extracts system from request using representation."""

    async def embed(self, request) -> Any:
        raise CapabilityNotSupportedError(
            "Anthropic does not support embeddings"
        )

    def normalize_response(self, raw) -> Any:
        """Convert Anthropic content blocks to workstation format."""

    def map_error(self, exc) -> ProviderError:
        """401 → AuthError, 429 → RateLimitError, etc."""
```

## Acceptance criteria

- [ ] `embed()` raises `CapabilityNotSupportedError` immediately, no HTTP call
- [ ] `x-api-key` and `anthropic-version` headers sent on every request
- [ ] `normalize_response()` correctly extracts text + tool_use content blocks
- [ ] `map_error()` handles all Anthropic HTTP status codes
- [ ] Unit tests with httpx mock
- [ ] `lint_code` + `type_check_code` pass
