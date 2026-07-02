# STEP-10 — documentation_slot_builder.py: implement STUB

**File:** `src/mwps/documentation_slot_builder.py`  
**Size:** 44 lines  
**Issues:** 2× STUB in `build()` method (lines 25, 31) — returns placeholder content  
**Severity:** 🔴 High (documentation context slot is non-functional)  
**Depends on:** —  
**Blocks:** —

---

## Current structure

| Entity | Lines | Responsibility |
|--------|-------|----------------|
| `DocumentationSlotBuilder.__init__` | 21–23 | Store `documentation_source` |
| `DocumentationSlotBuilder.build` | 25–44 | ⚠️ Build doc content segments — STUB |

## Problem

`build()` contains STUB markers (lines 25 and 31) indicating the method should:
> Return ordered doc content segments (canon first, then clarifications)

The stub likely returns an empty list or placeholder string instead of
actually querying the `documentation_source` for relevant documentation.

This means the documentation context slot in the model's prompt is always empty,
degrading model quality for documentation-heavy use cases.

## Task

### 10a. Understand `documentation_source`

Read `src/mwps/documentation_source.py` to understand the API:
- What does `DocumentationSource` provide?
- What query interface does it expose? (`get_canonical()`, `get_clarifications()`, etc.)
- What is the return type of each method?

### 10b. Implement `build()`

Based on the docstring hint "canon first, then clarifications":
```python
def build(self, query: str | None = None) -> list[str]:
    """
    Return ordered documentation segments: canonical docs first, then clarifications.

    Args:
        query: Optional search query to filter relevant docs.

    Returns:
        List of documentation text segments in priority order.
    """
    segments = []
    segments.extend(self._source.get_canonical(query=query))
    segments.extend(self._source.get_clarifications(query=query))
    return segments
```

Adapt signature and implementation to actual `DocumentationSource` API.

## Acceptance criteria

- [ ] Both STUB markers removed
- [ ] `build()` returns actual content from `documentation_source`
- [ ] Return type annotated
- [ ] Docstring complete (Args + Returns)
- [ ] `lint_code` + `type_check_code` pass
