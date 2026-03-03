<!--
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
-->

# Step 04: Abstract Base Class for Provider Clients

## Target file

- `src/ollama_workstation/provider_client_base.py` (canonical path in [SCOPE_FREEZE.md](SCOPE_FREEZE.md))

## Dependencies

- [SCOPE_FREEZE.md](SCOPE_FREEZE.md)
- [step_01_client_standard_document.md](step_01_client_standard_document.md)
- [step_03_uniform_error_model.md](step_03_uniform_error_model.md)
- [../QUALITY_GATE.md](../QUALITY_GATE.md)

## Detailed scope

- Implement abstract base class defining:
  - `validate_config()`, `healthcheck()`, `chat(request)`, `embed(request)`, `supports_tools()`, `normalize_response(raw_response)`, `map_error(exception)`.
  - Capability flags: `supports_stream`, `supports_tools`, `supports_embeddings` (property or attribute).
  - Contract aligned with provider_client_standard; embed mandatory (unsupported clients raise defined error from step_03).
- Use provider_errors from step_03 for error mapping.
- No `pass` in production; abstract methods use `NotImplemented` only where appropriate.

## Success metric

- Base class exists and is importable.
- All required methods and capability flags are defined; abstract methods clearly marked.
- Concrete client (step_08) can subclass and implement contract without redefining the interface.

## Blocking protocol (mandatory)

- If any requirement is unclear, contradictory, or underspecified: **STOP** implementation.
- Ask a clarifying question and proceed only after explicit clarification.
