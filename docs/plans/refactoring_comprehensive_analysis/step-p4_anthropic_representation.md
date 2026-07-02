# STEP-P4 — AnthropicRepresentation (new file)

**File:** `src/mwps/anthropic_representation.py` (new)
**Severity:** 🔴 High
**Depends on:** STEP-P1

---

## Tool format (Anthropic)

```json
{
  "name": "tool_name",
  "description": "...",
  "input_schema": { "type": "object", "properties": {...} }
}
```

## Message format (Anthropic)

Anthropic uses `system` as a top-level string (not a message), and
separate `messages` array with roles `user` / `assistant`. Tool use:

```json
[
  {"role": "assistant", "content": [
    {"type": "tool_use", "id": "toolu_01", "name": "...", "input": {...}}
  ]},
  {"role": "user", "content": [
    {"type": "tool_result", "tool_use_id": "toolu_01", "content": "..."}
  ]}
]
```

Note: system message is extracted from the messages list and passed
separately to the API (`AnthropicProviderClient` handles this).
`AnthropicRepresentation.serialize_messages()` returns only
`user`/`assistant` messages; system is returned separately.

## Task

```python
class AnthropicRepresentation(ContextRepresentation):
    """Serialize tools and messages for Anthropic Messages API."""

    def serialize_tools(self, tool_list) -> list[dict]:
        """Convert to Anthropic tool format (input_schema instead of parameters)."""

    def serialize_messages(self, messages) -> list[dict]:
        """Convert to Anthropic messages format.
        System message extracted and available via get_system_prompt().
        """

    def get_system_prompt(self, messages) -> str | None:
        """Extract system content from messages for top-level system param."""

    def format_tool_result(self, raw_result) -> str:
        """Serialize tool result for tool_result content."""


def register_anthropic_models(registry: RepresentationRegistry) -> None:
    rep = AnthropicRepresentation()
    for prefix in ("claude-",):
        registry.register(prefix, rep)
```

## Acceptance criteria

- [ ] Tool format uses `input_schema` (not `parameters`)
- [ ] System message extracted from messages list
- [ ] Tool use / tool result round-trip correct
- [ ] Unit tests
- [ ] `lint_code` + `type_check_code` pass
