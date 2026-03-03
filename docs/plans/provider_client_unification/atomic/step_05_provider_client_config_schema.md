<!--
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
-->

# Step 05: Provider Client Config Schema

## Target file

- `src/ollama_workstation/provider_client_config_schema.py` (canonical path in [SCOPE_FREEZE.md](SCOPE_FREEZE.md)).

## Dependencies

- [SCOPE_FREEZE.md](SCOPE_FREEZE.md)
- [step_02_config_standard_document.md](step_02_config_standard_document.md)
- [../QUALITY_GATE.md](../QUALITY_GATE.md)

## Detailed scope

- Define schema for `provider_clients` section: `default_provider`, `providers.<name>.transport`, `.auth`, `.tls`, `.features`, `.limits`.
- Schema must be usable by validator (step_06) and generator (step_07); format (e.g. JSON Schema, Pydantic) per project standards.
- Align with config standard document.

## Success metric

- Schema module exists; schema validates allowed structure and rejects invalid keys/types where applicable.
- Validator and generator steps can consume this schema.

## Blocking protocol (mandatory)

- If any requirement is unclear, contradictory, or underspecified: **STOP** implementation.
- Ask a clarifying question and proceed only after explicit clarification.
