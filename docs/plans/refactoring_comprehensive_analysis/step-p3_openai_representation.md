# STEP-P3 — OpenAIRepresentation (new file)

**File:** `src/mwps/openai_representation.py` (new)
**Severity:** 🔴 High
**Depends on:** STEP-P1 (registry enforced before adding new representations)
**Used by:** STEP-I1 (OpenAI client), STEP-I4 (xAI), STEP-I5 (DeepSeek)

---

## Context

OpenAI, xAI, DeepSeek all use the same tool and message format.
`OpenAIRepresentation` is the shared base; xAI and DeepSeek inherit
without overrides unless behaviour diverges.

## Tool format (OpenAI)

```json
{
  "type": "function",
  "function": {
    "name": "tool_name",
    "description": "...",
    "parameters": { ...json_schema... }
  }
}
```

## Message format (OpenAI)

```json
[
  {"role": "system", "content": "..."},
  {"role": "user", "content": "..."},
  {"role": "assistant", "content": null, "tool_calls": [
    {"id": "call_abc", "type": "function",
     "function": {"name": "...", "arguments": "{...}"}}
  ]},
  {"role": "tool", "tool_call_id": "call_abc", "content": "..."}
]
```

## Task

```python
class OpenAIRepresentation(ContextRepresentation):
    """Serialize tools and messages for OpenAI-compatible APIs."""

    def serialize_tools(self, tool_list) -> list[dict]:
        """Convert to OpenAI tool format."""

    def serialize_messages(self, messages) -> list[dict]:
        """Convert workstation-internal messages to OpenAI role/content format.
        Handles: system, user, assistant, tool_calls, tool results.
        """

    def format_tool_result(self, raw_result) -> str:
        """Serialize tool result as string for tool message content."""


class XAIRepresentation(OpenAIRepresentation):
    """xAI Grok — OpenAI-compatible, no overrides needed currently."""


class DeepSeekRepresentation(OpenAIRepresentation):
    """DeepSeek — OpenAI-compatible, no overrides needed currently."""


def register_openai_models(registry: RepresentationRegistry) -> None:
    """Register OpenAI-family representations for known model prefixes."""
    for prefix in ("gpt-", "o1", "o3", "o4"):
        registry.register(prefix, OpenAIRepresentation())
    registry.register("grok", XAIRepresentation())
    registry.register("deepseek", DeepSeekRepresentation())
```

## Acceptance criteria

- [ ] `OpenAIRepresentation` implements all 3 abstract methods
- [ ] Tool format matches OpenAI spec (type/function/name/description/parameters)
- [ ] Message format handles all roles including tool_calls and tool results
- [ ] `XAIRepresentation` and `DeepSeekRepresentation` inherit without override
- [ ] Registered in registry by known model prefixes
- [ ] Unit tests: serialize round-trip for a simple chat + tool call
- [ ] `lint_code` + `type_check_code` pass
