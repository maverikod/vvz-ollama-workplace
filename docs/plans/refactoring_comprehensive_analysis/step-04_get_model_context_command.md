# STEP-04 — get_model_context_command.py: split + fix placeholder

**File:** `src/ollama_workstation/commands/get_model_context_command.py`  
**Size:** 415 lines (+15 over limit)  
**Issues:** Long file; PLACEHOLDER in parameter schema (line 93); `execute` 158 lines  
**Severity:** 🔴 High + 🟡 Medium  
**Depends on:** —  
**Blocks:** —

---

## Current structure

| Entity | Lines | Responsibility |
|--------|-------|----------------|
| `_messages_for_display` (free func) | 43–55 (13) | Format messages for display |
| `GetModelContextCommand.get_schema` | 76–102 (27) | Input schema — contains PLACEHOLDER |
| `GetModelContextCommand.get_result_schema` | 105–183 (79) | Result schema — very large inline dict |
| `GetModelContextCommand.get_error_schema` | 186–196 (11) | Error schema |
| `GetModelContextCommand.get_metadata` | 199–256 (58) | Metadata — large inline dict |
| `GetModelContextCommand.execute` | 258–415 (158) | ⚠️ Full context build pipeline |

## Problems

**1. PLACEHOLDER in `get_schema`** (line 93)
```
PLACEHOLDER: Optional user message text to append as the last message, as ollama_ch...
```
The parameter description is truncated/unfinished. Must be completed.

**2. `get_result_schema` is 79 lines** — a single method with a deeply nested JSON Schema literal. Move to a `_schema.py` module.

**3. `execute` is 158 lines** covering:
- Session load
- Tool list construction (same pipeline as `OllamaChatCommand`)
- Message serialization
- Context assembly and return

## Task

### 4a. Fix PLACEHOLDER

Complete the parameter description at line 93. Based on context with `ollama_chat_command`, the parameter is `append_user_message: Optional[str]` — an optional text appended as the final user message before context snapshot.

### 4b. Extract schemas

Create `get_model_context_schema.py` with:
```python
INPUT_SCHEMA: dict = { ... }    # from get_schema
RESULT_SCHEMA: dict = { ... }   # from get_result_schema (79 lines)
ERROR_SCHEMA: dict = { ... }    # from get_error_schema
METADATA: dict = { ... }        # from get_metadata
```
Import in `GetModelContextCommand`.

### 4c. Decompose `execute`

Extract:
```
_load_session_for_context(session_id, ...) -> Session
_build_tool_list_for_context(session, discovery) -> list
_serialize_messages(messages, model) -> list
execute(...)  # orchestrator <40 lines
```

Target: file ≤ 200 lines after schema extraction, no method >60 lines.

## Acceptance criteria

- [ ] PLACEHOLDER at line 93 replaced with complete description
- [ ] Schemas moved to `get_model_context_schema.py`
- [ ] `execute` decomposed to <60 lines
- [ ] File total ≤ 400 lines
- [ ] `lint_code` + `type_check_code` pass
