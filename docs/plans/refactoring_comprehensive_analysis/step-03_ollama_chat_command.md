# STEP-03 — ollama_chat_command.py: split + deduplicate schema methods

**File:** `src/ollama_workstation/commands/ollama_chat_command.py`  
**Size:** 476 lines (+76 over limit)  
**Issues:** Long file; `_execute_session_mode` 232 lines; 3 near-identical schema methods  
**Severity:** 🔴 High + 🟡 Medium  
**Depends on:** STEP-01 (chat_flow refactored before splitting command)  
**Blocks:** —

---

## Current structure

| Method | Lines | Responsibility |
|--------|-------|----------------|
| `get_schema` | 76–83 (8) | Input JSON Schema — **DUPLICATE pattern** |
| `get_result_schema` | 86–93 (8) | Result JSON Schema — **DUPLICATE pattern** |
| `get_error_schema` | 96–103 (8) | Error JSON Schema — **DUPLICATE pattern** |
| `get_metadata` | 106–117 (12) | Command metadata for discovery |
| `execute` | 119–243 (125) | Entry point: validate, dispatch to session or direct |
| `_execute_session_mode` | 245–476 (232) | ⚠️ Full session chat: load session, run flow, save |

## Problems

**1. Three schema methods with identical structure** (similarity 1.0)
`get_schema`, `get_result_schema`, `get_error_schema` all follow the same pattern:
```python
@classmethod
def get_*_schema(cls) -> dict:
    return { ... large inline dict ... }
```
These should each live in a dedicated `ollama_chat_schema.py` (already exists — verify if it's used).

**2. `_execute_session_mode` is 232 lines** covering:
- Session load + validation
- Context build (history, tools, docs)
- `run_chat_flow` invocation
- Result extraction and session update

## Task

### 3a. Move schemas to ollama_chat_schema.py

`ollama_chat_schema.py` already exists. Move the three schema dicts there as module-level constants or functions. Import them in `OllamaChatCommand`.

### 3b. Decompose `_execute_session_mode`

Extract:
```
_load_and_validate_session(session_id, model_container) -> Session
_build_chat_context(session, model_container) -> ChatContext
_save_chat_result(session, result, session_store) -> None
_execute_session_mode(...)  # orchestrator only, <50 lines
```

Target: no method > 80 lines, file ≤ 400 lines.

## Acceptance criteria

- [ ] Schema dicts moved to `ollama_chat_schema.py`, imported back
- [ ] `_execute_session_mode` reduced to orchestrator ≤50 lines
- [ ] File total ≤ 400 lines
- [ ] `lint_code` + `type_check_code` pass
