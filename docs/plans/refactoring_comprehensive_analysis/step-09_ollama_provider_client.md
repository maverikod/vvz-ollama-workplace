# STEP-09 — ollama_provider_client.py: eliminate normalize_response duplicate

**File:** `src/ollama_workstation/ollama_provider_client.py`  
**Size:** 233 lines (within limit)  
**Issues:** `normalize_response` and `_normalize_embed_response` have similarity 1.0  
**Severity:** 🟡 Medium  
**Depends on:** STEP-08 (base class must be ABC before fixing concrete impl)  
**Blocks:** —

---

## Current structure

| Method | Lines | Responsibility |
|--------|-------|----------------|
| `normalize_response` | 206–227 (22) | Convert chat response to Ollama format |
| `_normalize_embed_response` | 229–243 (15) | Convert embed response to Ollama format |

## Problem

Both methods perform the same structural operation: take a raw provider response dict,
extract fields, build a normalized Ollama-format dict. Detected similarity is 1.0 —
bodies are structurally identical despite handling chat vs embed responses.

Likely cause: both use the same field-extraction pattern with fallbacks:
```python
result = {}
result["field"] = raw.get("field") or raw.get("alt_field", default)
...
return result
```

## Task

### 9a. Extract common normalization helper

```python
def _extract_fields(
    raw: dict,
    mapping: dict[str, tuple[str, ...]],
    defaults: dict[str, Any] | None = None,
) -> dict:
    """Extract fields from raw dict using primary/fallback key tuples."""
    result = {}
    for out_key, in_keys in mapping.items():
        for k in in_keys:
            if k in raw:
                result[out_key] = raw[k]
                break
        else:
            result[out_key] = (defaults or {}).get(out_key)
    return result
```

### 9b. Rewrite both methods using helper

`normalize_response` and `_normalize_embed_response` each become 5–10 lines
that define their specific field mapping and call `_extract_fields`.

## Acceptance criteria

- [ ] `normalize_response` and `_normalize_embed_response` share no duplicated logic
- [ ] Both methods ≤10 lines each
- [ ] Behavior identical to before (same output for same input)
- [ ] `lint_code` + `type_check_code` pass
