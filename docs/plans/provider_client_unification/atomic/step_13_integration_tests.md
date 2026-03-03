<!--
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
-->

# Step 13: Integration Tests

## Target file

- `tests/integration/test_provider_client_unification.py` (canonical path in [SCOPE_FREEZE.md](SCOPE_FREEZE.md); may be split into several files if needed).

## Dependencies

- [SCOPE_FREEZE.md](SCOPE_FREEZE.md)
- [step_01_client_standard_document.md](step_01_client_standard_document.md)
- [step_02_config_standard_document.md](step_02_config_standard_document.md)
- [step_03_uniform_error_model.md](step_03_uniform_error_model.md)
- [step_04_abstract_base_class.md](step_04_abstract_base_class.md)
- [step_05_provider_client_config_schema.md](step_05_provider_client_config_schema.md)
- [step_06_provider_client_config_validator.md](step_06_provider_client_config_validator.md)
- [step_07_provider_client_config_generator.md](step_07_provider_client_config_generator.md)
- [step_08_ollama_provider_client.md](step_08_ollama_provider_client.md)
- [step_09_provider_client_registry.md](step_09_provider_client_registry.md)
- [step_10_workstation_orchestration_refactor.md](step_10_workstation_orchestration_refactor.md)
- [step_11_database_server_full_surface.md](step_11_database_server_full_surface.md)
- [step_12_ollama_server_full_surface.md](step_12_ollama_server_full_surface.md)
- [../QUALITY_GATE.md](../QUALITY_GATE.md)
- [../CLIENT_UNIFICATION_TZ.md](../CLIENT_UNIFICATION_TZ.md) (Acceptance Criteria, Implementation Deliverable 7)
- [../TRACEABILITY_MATRIX.md](../TRACEABILITY_MATRIX.md) (§ Step documents)

## Detailed scope

- Integration tests covering:
  1. **No-direct-access policy:** workstation has no direct redis/ollama path in runtime; test fails when direct access is introduced (or test asserts absence of direct calls in code paths used by model).
  2. **Provider parity via common API:** model interaction for configured providers is performed via provider clients only; at least one provider (e.g. Ollama) exercised through common API.
  3. **Proxy registration and command availability:** database-server and ollama-server are proxy-registered; command catalogs discoverable; key commands callable via call_server with real or test backend as agreed.
- Tests may use real services (proxy, adapter, redis, ollama) or documented test doubles where the plan allows; prefer real where feasible per TZ acceptance criteria.

## Success metric

- All integration tests listed above exist and pass.
- No-direct-access test is green when orchestration uses only provider clients and proxy; fails (or would fail) if direct redis/ollama path is reintroduced.
- Proxy registration tests confirm database-server and ollama-server visible and callable.

## Blocking protocol (mandatory)

- If any requirement is unclear, contradictory, or underspecified: **STOP** implementation.
- Ask a clarifying question and proceed only after explicit clarification.
