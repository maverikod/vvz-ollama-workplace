# STEP-P5 — GeminiRepresentation (new file)

**File:** `src/ollama_workstation/gemini_representation.py` (new)
**Severity:** 🔴 High
**Depends on:** STEP-P1
**Related to:** STEP-I3 (GoogleProviderClient uses this representation)

---

## Gemini API specifics

Gemini uses a different schema for both tools and messages.

## Tool format (Gemini)

```json
{
  "function_declarations": [
    {
      "name": "tool_name",
      "description": "...",
      "parameters": { "type": "OBJECT", "properties": {...} }
    }
  ]
}
```

Tools are grouped under `function_declarations` inside a `tools` array,
not listed individually. Parameter types use Gemini enum strings
(`"STRING"`, `"INTEGER"`, `"OBJECT"`, etc.) not JSON Schema strings.

## Message format (Gemini)

```json
{
  "contents": [
    {"role": "user",  "parts": [{"text": "..."}]},
    {"role": "model", "parts": [
      {"functionCall": {"name": "...", "args": {...}}}
    ]},
    {"role": "user",  "parts": [
      {"functionResponse": {"name": "...", "response": {"content": "..."}}}
    ]}
  ],
  "systemInstruction": {"parts": [{"text": "..."}]}
}
```

Key differences from OpenAI/Anthropic:
- Role is `"model"` (not `"assistant"`)
- Tool call is `functionCall` inside `parts`
- Tool result is `functionResponse` inside `parts` with `role: user`
- System prompt is `systemInstruction` (top-level, not a message)

## Task

```python
class GeminiRepresentation(ContextRepresentation):
    """Serialize tools and messages for Google Gemini API."""

    def serialize_tools(self, tool_list) -> list[dict]:
        """Convert to Gemini function_declarations format.
        Returns [{"function_declarations": [...]}].
        Maps JSON Schema types to Gemini type enums.
        """

    def serialize_messages(self, messages) -> list[dict]:
        """Convert to Gemini contents format.
        role=user/model; tool calls as functionCall parts;
        tool results as functionResponse parts with role=user.
        System message extracted for systemInstruction.
        """

    def get_system_instruction(self, messages) -> dict | None:
        """Extract system content as Gemini systemInstruction object."""

    def format_tool_result(self, raw_result) -> str:
        """Serialize tool result for functionResponse.response.content."""

    @staticmethod
    def _map_json_type(json_type: str) -> str:
        """Map JSON Schema type string to Gemini type enum."""
        # "string" -> "STRING", "integer" -> "INTEGER", "object" -> "OBJECT", etc.


def register_gemini_models(registry: RepresentationRegistry) -> None:
    rep = GeminiRepresentation()
    for prefix in ("gemini-",):
        registry.register(prefix, rep)
```

## Acceptance criteria

- [ ] Tools wrapped in `function_declarations`
- [ ] JSON Schema types mapped to Gemini enums
- [ ] `role: model` used for assistant messages
- [ ] `functionCall` / `functionResponse` round-trip correct
- [ ] `systemInstruction` extracted from messages
- [ ] Unit tests: tool serialization + message with function call
- [ ] `lint_code` + `type_check_code` pass
