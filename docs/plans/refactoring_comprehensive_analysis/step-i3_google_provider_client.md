# STEP-I3 — GoogleProviderClient (new file)

**File:** `src/ollama_workstation/google_provider_client.py` (new)
**Provider:** `google` — Gemini API only (NOT Vertex AI)
**Severity:** 🔴 High
**Depends on:** STEP-08, STEP-P5 (GeminiRepresentation)

---

## API specifics

| Param | Value |
|-------|-------|
| Base URL | `https://generativelanguage.googleapis.com` |
| API version | `v1beta` (configurable) |
| Chat endpoint | `POST /{version}/models/{model}:generateContent?key={api_key}` |
| Embed endpoint | `POST /{version}/models/{embed_model}:embedContent?key={api_key}` |
| Auth | `?key=` query param OR `Authorization: Bearer {service_account_token}` |
| Embed support | **Yes** (`text-embedding-004`) |

## Chat request shape

```json
{
  "contents": [
    {"role": "user",  "parts": [{"text": "Hello"}]},
    {"role": "model", "parts": [
      {"functionCall": {"name": "search", "args": {"q": "..."}}}]
    },
    {"role": "user",  "parts": [
      {"functionResponse": {"name": "search", "response": {"content": "..."}}}]
    }
  ],
  "systemInstruction": {"parts": [{"text": "You are..."}]},
  "tools": [{"function_declarations": [{"name": "...", "description": "...", "parameters": {...}}]}],
  "generationConfig": {"maxOutputTokens": 8192},
  "safetySettings": []
}
```

## Embed request shape

```json
{
  "model": "models/text-embedding-004",
  "content": {"parts": [{"text": "query text"}]}
}
```
Response: `{"embedding": {"values": [0.1, 0.2, ...]}}`

## Response normalization

Gemini returns:
```json
{
  "candidates": [{
    "content": {
      "role": "model",
      "parts": [
        {"text": "..."},
        {"functionCall": {"name": "...", "args": {...}}}
      ]
    },
    "finishReason": "STOP" | "FUNCTION_CALL"
  }]
}
```
`normalize_response()` converts to workstation-internal format
(same shape as OpenAI/Anthropic normalization output).

## Safety settings

`config.features.safety_settings` is a list of
`{"category": "HARM_CATEGORY_*", "threshold": "BLOCK_*"}` dicts.
Passed as `safetySettings` in every request. Empty list = Gemini defaults.

## Task

```python
class GoogleProviderClient(BaseProviderClient):
    """Google Gemini API client (generativelanguage.googleapis.com).
    NOT compatible with Vertex AI.
    """

    @property
    def supports_stream(self) -> bool: return True
    @property
    def supports_tools(self) -> bool: return True
    @property
    def supports_embeddings(self) -> bool: return True

    def validate_config(self) -> None:
        """Check api_key non-empty (or service_account_json set, not both)."""

    def healthcheck(self) -> bool:
        """GET /{version}/models?key={api_key}, expect 200."""

    async def chat(self, request) -> Any:
        """POST :generateContent with Gemini-format body.
        Representation (GeminiRepresentation) builds the body shape;
        client adds generationConfig, safetySettings, auth.
        """

    async def embed(self, request) -> Any:
        """POST :embedContent, return flat list of floats."""

    def normalize_response(self, raw) -> Any:
        """Convert Gemini candidates[0].content to workstation format."""

    def map_error(self, exc) -> ProviderError:
        """400 → ValidationError, 401/403 → AuthError, 429 → RateLimitError."""

    def _build_url(self, model: str, method: str) -> str:
        """Build endpoint URL: /{version}/models/{model}:{method}?key=..."""
```

## Acceptance criteria

- [ ] Auth via `?key=` query param (primary path; service account deferred)
- [ ] `embed()` returns flat `list[float]` from `embedding.values`
- [ ] `normalize_response()` handles text + functionCall parts
- [ ] `safetySettings` from config passed in every request
- [ ] `validate_config()` raises `ValidationError` if both api_key and
  service_account_json set simultaneously
- [ ] `map_error()` handles Gemini HTTP status codes
- [ ] Unit tests with httpx mock
- [ ] `lint_code` + `type_check_code` pass
