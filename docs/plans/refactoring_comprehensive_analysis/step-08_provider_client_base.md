# STEP-08 — provider_client_base.py: eliminate duplicate abstract method bodies

**File:** `src/ollama_workstation/provider_client_base.py`  
**Size:** 118 lines  
**Issues:** `chat`, `embed`, `normalize_response` have similarity 1.0 — identical abstract stubs  
**Severity:** 🟡 Medium  
**Depends on:** STEP-06, STEP-07 (provider chain must work before hardening base class)  
**Blocks:** STEP-09

---

## Current structure

| Method | Lines | Body |
|--------|-------|------|
| `supports_stream` | 31–33 | Returns `True` by default |
| `supports_tools` | 36–38 | Returns `True` by default |
| `supports_embeddings` | 42–48 | Returns `False` by default |
| `validate_config` | 53–61 | Abstract — raises `NotImplementedError` |
| `healthcheck` | 64–72 | Abstract — raises `NotImplementedError` |
| `chat` | 77–85 | Abstract — raises `NotImplementedError` — **DUPLICATE body** |
| `embed` | 88–95 | Abstract — raises `NotImplementedError` — **DUPLICATE body** |
| `normalize_response` | 100–106 | Abstract — raises `NotImplementedError` — **DUPLICATE body** |
| `map_error` | 109–118 | Abstract — raises `NotImplementedError` |

## Problem

`chat`, `embed`, `normalize_response` (and likely `validate_config`, `healthcheck`, `map_error`) all have the same body:
```python
raise NotImplementedError(f"{self.__class__.__name__} must implement {method_name}")
```
This is the signature of an abstract base class that doesn't use `@abstractmethod`. It should.

The duplicate detection flags these three because their bodies are structurally identical.

## Task

Convert `BaseProviderClient` to a proper ABC with `@abstractmethod` decorators:

```python
from abc import ABC, abstractmethod

class BaseProviderClient(ABC):

    @abstractmethod
    async def chat(self, messages: list, model: str, **kwargs) -> dict:
        """Send chat completion request."""

    @abstractmethod
    async def embed(self, input_: str | list[str], model: str) -> list[list[float]]:
        """Generate embeddings."""

    @abstractmethod
    def normalize_response(self, raw: dict) -> dict:
        """Normalize provider response to Ollama format."""

    @abstractmethod
    async def validate_config(self) -> None: ...

    @abstractmethod
    async def healthcheck(self) -> bool: ...

    @abstractmethod
    def map_error(self, exc: Exception) -> Exception: ...
```

Remove all `raise NotImplementedError(...)` bodies from abstract methods.
Keep concrete defaults for `supports_stream`, `supports_tools`, `supports_embeddings`.

## Acceptance criteria

- [ ] `BaseProviderClient` uses `ABC` + `@abstractmethod`
- [ ] No duplicate `raise NotImplementedError` bodies
- [ ] `OllamaProviderClient` still passes `isinstance(client, BaseProviderClient)`
- [ ] `lint_code` + `type_check_code` pass
- [ ] `mypy` does not report missing abstract implementations
