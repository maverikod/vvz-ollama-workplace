<!--
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
-->

# Step 09: Provider Client Registry

## Target file

- `src/ollama_workstation/provider_registry.py` (canonical path in [SCOPE_FREEZE.md](SCOPE_FREEZE.md))

## Dependencies

- [SCOPE_FREEZE.md](SCOPE_FREEZE.md)
- [step_04_abstract_base_class.md](step_04_abstract_base_class.md)
- [step_06_provider_client_config_validator.md](step_06_provider_client_config_validator.md)
- [../QUALITY_GATE.md](../QUALITY_GATE.md)

## Detailed scope

- Implement registry or factory that, given provider name (and config), returns the appropriate provider client instance (base class type).
- Config-driven: active provider and provider_clients sections used to build clients; validation errors from step_06 must prevent creating invalid clients.
- Workstation orchestration can resolve client by default_provider or by explicit provider name.

## Success metric

- Registry returns a valid provider client for configured provider name(s); invalid config leads to clear error (no silent wrong client).
- Workstation can obtain Ollama client (and optionally others) via registry for use in step_10.

## Blocking protocol (mandatory)

- If any requirement is unclear, contradictory, or underspecified: **STOP** implementation.
- Ask a clarifying question and proceed only after explicit clarification.
