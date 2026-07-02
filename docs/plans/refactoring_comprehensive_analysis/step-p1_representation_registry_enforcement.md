# STEP-P1 — Enforce RepresentationRegistry everywhere (fix P1 + P5)

**Concern:** `chat_flow.py`, `mwps_chat_command.py`, `get_model_context_command.py`, `tools.py`
**Issues:** P1 (MwpsRepresentation hardcoded in 4 files, 25 usages), P5 (tools.py Model Workplace Server-format hardcoded)
**Severity:** 🔴 High — blocks adding any second provider
**Depends on:** — (pure refactor, no new code needed)
**Blocks:** STEP-01, STEP-03, STEP-04, STEP-P3, STEP-P4, STEP-P5

---

## Current violations (from find_usages)

| File | Line | Violation |
|------|------|-----------|
| `chat_flow.py` | 23, 292 | `from .mwps_representation import MwpsRepresentation` |
| `chat_flow.py` | 138 | `MwpsRepresentation()` in `run_tool_like_model` |
| `chat_flow.py` | 294 | `MwpsRepresentation()` in `run_chat_flow` |
| `mwps_chat_command.py` | 38, 291 | direct import + instantiation in `_execute_session_mode` |
| `get_model_context_command.py` | 27, 299 | direct import + instantiation in `execute` |
| `tools.py` | entire file | `get_mwps_tools()` hardcodes Model Workplace Server tool format |
| `scripts/check_tools_access.py` | 37, 147 | direct import + instantiation |
| `scripts/verify_context_formation.py` | 27, 79 | direct import + instantiation |
| `scripts/verify_context_limits.py` | 27, 55 | direct import + instantiation |

## Task

### P1a. Inject RepresentationRegistry into run_chat_flow

`run_chat_flow` must receive a `RepresentationRegistry` instance (not
create `MwpsRepresentation()` itself). The registry is built once
during workstation initialization and passed to the flow.

```python
def run_chat_flow(
    ...,
    representation_registry: RepresentationRegistry,
    model_id: str,
) -> ...
    representation = representation_registry.get_representation(model_id)
    # use representation.serialize_tools(), .serialize_messages(), .format_tool_result()
```

Same change in `run_tool_like_model`: receives registry + model_id,
not hardcoded MwpsRepresentation.

### P1b. Pass registry through MwpsChatCommand and GetModelContextCommand

Both commands must build or receive `RepresentationRegistry` and pass
it to `run_chat_flow`. Model id comes from the session.

### P1c. Replace tools.py

`get_mwps_tools()` → `get_tools_for_model(model_id: str, registry: RepresentationRegistry) -> list[dict]`

Internally: discovers available commands, calls
`registry.get_representation(model_id).serialize_tools(tool_list)`.
No Model Workplace Server-format hardcoded.

### P1d. Fix scripts

Scripts that instantiate `MwpsRepresentation()` directly should
instead build a registry with `MwpsRepresentation` registered and
call `registry.get_representation(model_id)`. Scripts are
diagnostic-only so this is a one-liner change per file.

## Acceptance criteria

- [ ] Zero `import MwpsRepresentation` outside `mwps_representation.py`,
  `representation_registry` setup code, and tests
- [ ] `run_chat_flow` and `run_tool_like_model` receive `RepresentationRegistry`
- [ ] `get_tools_for_model(model_id, registry)` replaces `get_mwps_tools()`
- [ ] All callers updated (commands + scripts)
- [ ] `MwpsRepresentation` still registered and used for `mwps` models
- [ ] `lint_code` + `type_check_code` pass
