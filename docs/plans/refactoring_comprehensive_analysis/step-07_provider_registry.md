# STEP-07 — provider_registry.py: implement NOT IMPLEMENTED

**File:** `src/mwps/provider_registry.py`  
**Size:** 190 lines  
**Issues:** 3× NOT IMPLEMENTED — `get_client` raises for non-mwps providers; provider `mwps` unavailable via package  
**Severity:** 🔴 High (blocks all non-mwps providers)  
**Depends on:** STEP-06 (`commercial_chat_client` must be implemented first)  
**Blocks:** STEP-08

---

## Current structure

| Function | Lines | Responsibility |
|----------|-------|----------------|
| `_build_mwps` | 27–47 (21) | Construct `MwpsProviderClient` from config |
| `get_client` | 57–113 (57) | Resolve provider name → client instance |
| `get_default_client` | 116–143 (28) | Get client for config default model |
| `get_client_from_app_config` | 146–181 (36) | Get client from full app config |
| `list_supported_providers` | 184–190 (7) | Return list of supported provider names |

## Problems

**NOT IMPLEMENTED #1** (line 38): Inside `_build_mwps` — `mwps_provider_client` package import fails — the package `mwps_provider_client` is not installed in venv.

**NOT IMPLEMENTED #2** (line 57): `get_client` raises `NotImplementedError` for any provider other than `"mwps"`.

**NOT IMPLEMENTED #3** (line 63): The branch for provider `"mwps"` also hits `NotImplementedError` because `_build_mwps` fails.

## Task

### 7a. Fix `_build_mwps`

Replace import of unavailable `mwps_provider_client` package with direct use of `MwpsProviderClient` from `mwps.mwps_provider_client`:
```python
from .mwps_provider_client import MwpsProviderClient

def _build_mwps(config: WorkstationConfig) -> MwpsProviderClient:
    return MwpsProviderClient(
        base_url=config.model.mwps_url,
        model=config.model.mwps_model,
        timeout=config.model.request_timeout,
    )
```

### 7b. Implement `get_client` for commercial providers

Add branch for OpenAI-compatible providers using `commercial_chat_client`:
```python
if provider in ("openai", "anthropic", "groq", "mistral"):  # extend as needed
    return CommercialProviderClient(
        base_url=_provider_base_url(provider),
        api_key=_get_api_key(provider, config),
        model=model,
    )
```

Create thin `CommercialProviderClient(BaseProviderClient)` that wraps `commercial_chat_client.chat_completion`.

### 7c. Update `list_supported_providers`

Return actual list including commercial providers.

## Acceptance criteria

- [ ] All 3 NOT IMPLEMENTED markers removed
- [ ] `get_client("mwps", ...)` returns working `MwpsProviderClient`
- [ ] `get_client("openai", ...)` returns working `CommercialProviderClient`
- [ ] `list_supported_providers()` returns complete list
- [ ] `lint_code` + `type_check_code` pass
