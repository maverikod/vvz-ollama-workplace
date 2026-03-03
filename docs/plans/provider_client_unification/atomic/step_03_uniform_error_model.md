<!--
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
-->

# Step 03: Uniform Error Model

## Target file

- `src/ollama_workstation/provider_errors.py` (canonical path in [SCOPE_FREEZE.md](SCOPE_FREEZE.md))

## Dependencies

- [SCOPE_FREEZE.md](SCOPE_FREEZE.md)
- [../QUALITY_GATE.md](../QUALITY_GATE.md)
- [../CLIENT_UNIFICATION_TZ.md](../CLIENT_UNIFICATION_TZ.md) (AR-3), [step_01](step_01_client_standard_document.md) (error categories)

## Detailed scope

- Implement a single module defining shared exception classes for provider clients:
  - `TransportError`, `AuthError`, `TimeoutError`, `RateLimitError`, `ProviderProtocolError`, `ValidationError`.
  - Optionally `CapabilityNotSupportedError` (for unsupported `embed()` per TZ); if used, document in docstrings.
- All classes suitable for `map_error(exception)` to return or raise; no `pass` or `NotImplemented` in production code.
- File header and docstrings in English.

## Success metric

- Module exists; all listed error classes are defined and importable.
- No `pass`/`NotImplemented` in production code; docstrings present.
- Step 04 (abstract base) can import and use these errors.

## Blocking protocol (mandatory)

- If any requirement is unclear, contradictory, or underspecified: **STOP** implementation.
- Ask a clarifying question and proceed only after explicit clarification.
