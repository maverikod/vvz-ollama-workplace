# STEP-02 — config.py: split + merge duplicate parsers

**File:** `src/mwps/config.py`  
**Size:** 477 lines (+77 over limit)  
**Issues:** Long file; `load_config` 244 lines; dup `_parse_number`/`_parse_int`  
**Severity:** 🔴 High + 🟡 Medium  
**Depends on:** —  
**Blocks:** STEP-05

---

## Current structure

| Entity | Lines | Responsibility |
|--------|-------|----------------|
| `WorkstationConfig` (dataclass) | 41–147 (107) | All config fields + `__post_init__` validation |
| `_parse_number` | 150–157 (8) | Parse string to float/int — **DUPLICATE** |
| `_parse_int` | 160–167 (8) | Parse string to int — **DUPLICATE** |
| `_proxy_from_registration` | 170–200 (31) | Build proxy URL from registration config |
| `load_config` | 203–446 (244) | ⚠️ Monolith: reads env vars, YAML, merges, validates |
| `_load_commands_policy_config` | 449–477 (29) | Parse allowed/forbidden commands config |

## Problems

**1. Duplicate `_parse_number` / `_parse_int`** (similarity 1.0)
Both functions have identical structure: try cast, except return default.
`_parse_int` is a strict subset of `_parse_number`. Merge into one generic `_parse_scalar(value, type_, default)`.

**2. `load_config` is 244 lines** — reads env, YAML, merges sources, normalizes paths, builds sub-configs.
Contains at least 5 distinct loading phases.

## Task

### 2a. Merge duplicate parsers

Replace `_parse_number` + `_parse_int` with single:
```python
def _parse_scalar(value: str | None, type_: type, default: T) -> T:
    """Parse string value to scalar type; return default on failure."""
```
Update all call sites inside `load_config`.

### 2b. Decompose `load_config`

Extract private helpers:
```
_load_yaml_config(path) -> dict          # YAML loading + error handling
_load_env_overrides(cfg) -> dict         # env var extraction
_build_server_config(raw) -> dict        # server/proxy sub-section
_build_model_config(raw) -> dict         # model sub-section
_build_session_config(raw) -> dict       # session sub-section
load_config(path) -> WorkstationConfig   # orchestrator only, <50 lines
```

Target: no function > 60 lines, file stays under 400 lines.

## Acceptance criteria

- [ ] `_parse_number` and `_parse_int` removed, replaced by `_parse_scalar`
- [ ] `load_config` reduced to <60 lines (orchestrator only)
- [ ] Each extracted helper has docstring + type hints
- [ ] File total ≤ 400 lines
- [ ] `lint_code` + `type_check_code` pass
