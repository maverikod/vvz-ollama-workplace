<!--
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
-->

# Step 02: Config Standard Document

## Target file

- `docs/standards/provider_client_config_standard.md` (canonical path in [SCOPE_FREEZE.md](SCOPE_FREEZE.md))

## Dependencies

- [SCOPE_FREEZE.md](SCOPE_FREEZE.md)
- [../QUALITY_GATE.md](../QUALITY_GATE.md)
- [../CLIENT_UNIFICATION_TZ.md](../CLIENT_UNIFICATION_TZ.md) (Configuration Standard)

## Detailed scope

- Write normative document defining:
  - Normalized structure: `provider_clients.default_provider`, `provider_clients.providers.<provider_name>.transport`, `.auth`, `.tls`, `.features`, `.limits`.
  - Example provider names (ollama, openai, anthropic, google, xai, deepseek).
  - Validation rules: active provider section must exist and pass schema; auth and TLS requirements must match protocol/endpoint.
  - Rule: validation must reject incomplete or conflicting provider client settings before runtime.

## Success metric

- Document exists at the target path.
- It defines the full structure and validation rules.
- Steps 05–07 (schema, validator, generator) can be implemented by following this document alone.

## Blocking protocol (mandatory)

- If any requirement is unclear, contradictory, or underspecified: **STOP** implementation.
- Ask a clarifying question and proceed only after explicit clarification.
