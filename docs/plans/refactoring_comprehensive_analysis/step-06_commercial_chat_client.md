# STEP-06 — commercial_chat_client.py: implement NOT IMPLEMENTED

**File:** `src/mwps/commercial_chat_client.py`  
**Size:** 132 lines  
**Issues:** 2× NOT IMPLEMENTED in `chat_completion` (lines 66, 73) — function partially implemented  
**Severity:** 🔴 High (blocks functionality)  
**Depends on:** —  
**Blocks:** STEP-07

---

## Current structure

| Function | Lines | Responsibility |
|----------|-------|----------------|
| `_mwps_to_openai_messages` | 23–45 (23) | Convert Model Workplace Server message format to OpenAI format |
| `_openai_to_mwps_message` | 48–63 (16) | Convert OpenAI response to Model Workplace Server format |
| `chat_completion` | 66–132 (67) | ⚠️ Send to OpenAI-compatible endpoint — NOT IMPLEMENTED |

## Problem

`chat_completion` contains two `NOT IMPLEMENTED` markers (lines 66 and 73).
The function exists with converters but the actual HTTP call to the OpenAI-compatible
endpoint is not made. This means all commercial model providers (OpenAI, Anthropic, etc.)
are non-functional.

Context from `provider_registry.py`: `commercial_chat_client.chat_completion` is called
when the resolved provider is not `mwps`. This is the only code path for commercial models.

## Task

Implement `chat_completion`:

```python
async def chat_completion(
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    stream: bool = False,
    timeout: float = 120.0,
) -> dict:  # Model Workplace Server-format response
    """
    Send chat completion to OpenAI-compatible endpoint.
    Converts Model Workplace Server messages to OpenAI format, calls POST /v1/chat/completions,
    converts response back to Model Workplace Server format.
    """
    openai_messages = _mwps_to_openai_messages(messages)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{base_url}/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "messages": openai_messages, "tools": tools or [], "stream": stream},
        )
        response.raise_for_status()
    return _openai_to_mwps_message(response.json())
```

Handle errors: connection errors, 4xx/5xx, JSON parse failures.

## Acceptance criteria

- [ ] Both NOT IMPLEMENTED markers removed
- [ ] `chat_completion` makes actual HTTP call to OpenAI-compatible API
- [ ] Proper error handling: `httpx.HTTPError`, `KeyError`, timeout
- [ ] Response converted to Model Workplace Server format via `_openai_to_mwps_message`
- [ ] `lint_code` + `type_check_code` pass
