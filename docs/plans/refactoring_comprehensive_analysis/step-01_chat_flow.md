# STEP-01 — chat_flow.py: split long file

**File:** `src/ollama_workstation/chat_flow.py`  
**Size:** 609 lines (+209 over limit)  
**Issues:** Long file, monolithic `run_chat_flow` (lines 261–609, 349 lines)  
**Severity:** 🔴 High  
**Depends on:** —  
**Blocks:** STEP-03

---

## Current structure

| Function | Lines | Responsibility |
|----------|-------|----------------|
| `_tool_message` | 40–46 (7) | Build tool result message |
| `_run_tool` | 49–108 (60) | Execute one tool call via proxy |
| `run_tool` | 111–124 (14) | Public wrapper for `_run_tool` |
| `run_tool_like_model` | 127–191 (65) | Run tool exactly as model would |
| `_run_help_for_model` | 194–220 (27) | Execute help command for model |
| `_run_session_tool` | 223–258 (36) | Handle session-specific tools |
| `run_chat_flow` | 261–609 (349) | ⚠️ Entire chat loop: init, stream, tools, retries |

## Problem

`run_chat_flow` (349 lines) contains at least four distinct concerns:
1. **Initialization** — session load, context build, tool list preparation
2. **Request dispatch** — send to Ollama, handle streaming vs. non-streaming
3. **Tool loop** — detect tool calls, execute, append results, retry
4. **Result assembly** — collect final message, write to session store

## Task

Split `chat_flow.py` into a package `chat_flow/`:

```
src/ollama_workstation/chat_flow/
    __init__.py          # re-exports: run_chat_flow, run_tool, run_tool_like_model
    _messages.py         # _tool_message
    _tool_runner.py      # _run_tool, run_tool, run_tool_like_model,
                         # _run_help_for_model, _run_session_tool
    _chat_loop.py        # run_chat_flow split: init + dispatch + tool loop + result
```

Target: no file > 200 lines.

## Acceptance criteria

- [ ] `split_file_to_package` or manual split via CST
- [ ] All public names re-exported from `chat_flow/__init__.py`
- [ ] Existing imports in `ollama_chat_command.py` and `invoke_tool_command.py` unchanged
- [ ] `run_chat_flow` internally decomposed: each sub-concern is a private function
- [ ] No file exceeds 400 lines
- [ ] `lint_code` + `type_check_code` pass
