<!--
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
-->

# Step 06: Provider Client Config Validator

## Target file

- `src/ollama_workstation/provider_client_config_validator.py` (canonical path in [SCOPE_FREEZE.md](SCOPE_FREEZE.md))

## Dependencies

- [SCOPE_FREEZE.md](SCOPE_FREEZE.md)
- [step_02_config_standard_document.md](step_02_config_standard_document.md)
- [step_05_provider_client_config_schema.md](step_05_provider_client_config_schema.md)
- [../QUALITY_GATE.md](../QUALITY_GATE.md)
- [../CLIENT_UNIFICATION_TZ.md](../CLIENT_UNIFICATION_TZ.md) (FR-5: validation rejects incomplete/conflicting provider client settings before runtime)

## Detailed scope

- Implement validator for provider client config (provider_clients section).
- Reject incomplete or conflicting settings; align with auth/TLS vs protocol rules from config standard.
- Validator must be invokable before runtime (e.g. at startup or via CLI); validation errors block invalid startup per TZ.

## Success metric

- Validator runs on config and raises or returns clear errors for invalid/incomplete/conflicting provider_clients config.
- Valid config passes; invalid examples from config standard fail validation.
- Integration with workstation startup (fail fast on validation error) is possible or implemented; see [SCOPE_FREEZE.md](SCOPE_FREEZE.md) § Startup validation.

## Blocking protocol (mandatory)

- If any requirement is unclear, contradictory, or underspecified: **STOP** implementation.
- Ask a clarifying question and proceed only after explicit clarification.
