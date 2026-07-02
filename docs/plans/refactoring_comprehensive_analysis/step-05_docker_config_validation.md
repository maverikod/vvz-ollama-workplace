# STEP-05 — docker_config_validation.py: split monolith

**File:** `src/mwps/docker_config_validation.py`  
**Size:** 527 lines (+127 over limit)  
**Issues:** Long file; `validate_project_config` is 211 lines  
**Severity:** 🔴 High  
**Depends on:** STEP-02 (config.py refactored, may affect import paths)  
**Blocks:** —

---

## Current structure

| Function | Lines | Responsibility |
|----------|-------|----------------|
| `get_runtime_allowed_providers` | 75–112 (38) | Filter provider list by runtime availability |
| `_get_mwps_from_ow` | 115–134 (20) | Extract Model Workplace Server section from workstation config |
| `get_provider_for_model` | 137–145 (9) | Map model name to provider |
| `get_required_api_key_for_model` | 148–159 (12) | Return required API key env var for model |
| `_collect_providers_in_use` | 162–199 (38) | Enumerate providers referenced by config |
| `_collect_required_api_keys` | 202–229 (28) | Enumerate required API keys |
| `validate_model_providers` | 232–294 (63) | Validate all models have valid providers |
| `validate_commercial_model_keys` | 297–314 (18) | Check API keys present for commercial models |
| `validate_project_config` | 317–527 (211) | ⚠️ Full config validation: structure + models + keys + network |

## Problem

`validate_project_config` (211 lines) validates at least 5 independent aspects:
1. Top-level structure (required keys)
2. Model list and provider mapping
3. Commercial provider API keys
4. Network/server settings
5. Session and commands policy

## Task

Split into a package `docker_config_validation/`:

```
src/mwps/docker_config_validation/
    __init__.py                    # re-exports public API
    _providers.py                  # get_runtime_allowed_providers, _get_mwps_from_ow,
                                   # get_provider_for_model, _collect_providers_in_use
    _api_keys.py                   # get_required_api_key_for_model, _collect_required_api_keys,
                                   # validate_commercial_model_keys
    _validators.py                 # validate_model_providers, validate_project_config (decomposed)
```

Decompose `validate_project_config`:
```python
def _validate_structure(cfg: dict) -> list[str]: ...
def _validate_models(cfg: dict) -> list[str]: ...
def _validate_keys(cfg: dict) -> list[str]: ...
def _validate_network(cfg: dict) -> list[str]: ...
def validate_project_config(cfg: dict) -> ValidationResult:  # orchestrator <30 lines
    errors = []
    errors += _validate_structure(cfg)
    errors += _validate_models(cfg)
    ...
```

Target: no file >250 lines, no function >60 lines.

## Acceptance criteria

- [ ] Package structure created with `__init__.py` re-exporting public API
- [ ] `validate_project_config` decomposed, each validator <60 lines
- [ ] No file exceeds 400 lines
- [ ] All callers (docker scripts, tests) use same import paths via `__init__`
- [ ] `lint_code` + `type_check_code` pass
