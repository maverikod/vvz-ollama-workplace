<!--
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
-->

# Step 07: Provider Client Config Generator

## Target file

- `src/ollama_workstation/provider_client_config_generator.py` (canonical path in [SCOPE_FREEZE.md](SCOPE_FREEZE.md))

## Dependencies

- [SCOPE_FREEZE.md](SCOPE_FREEZE.md)
- [step_02_config_standard_document.md](step_02_config_standard_document.md)
- [step_05_provider_client_config_schema.md](step_05_provider_client_config_schema.md)
- [../QUALITY_GATE.md](../QUALITY_GATE.md)

## Detailed scope

- Implement generator that produces a valid `provider_clients` section (or full config including it).
- Output must conform to schema and config standard; suitable for validator (step_06) to accept.
- Support prompt-driven or template/example generation as per project practice.

## Success metric

- Generator produces output that passes the provider client config validator.
- Generated sample includes at least one provider (e.g. ollama) with transport/auth/tls/features/limits as per standard.

## Blocking protocol (mandatory)

- If any requirement is unclear, contradictory, or underspecified: **STOP** implementation.
- Ask a clarifying question and proceed only after explicit clarification.
