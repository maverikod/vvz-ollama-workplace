<!--
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
-->

# Provider Client Unification — Atomic Implementation Plan

Execution-ready plan for [CLIENT_UNIFICATION_TZ.md](../CLIENT_UNIFICATION_TZ.md). Shared gate: [../QUALITY_GATE.md](../QUALITY_GATE.md). Traceability: [../TRACEABILITY_MATRIX.md](../TRACEABILITY_MATRIX.md). Parallel chains: [PARALLEL_EXECUTION_CHAINS.md](./PARALLEL_EXECUTION_CHAINS.md).

## Step order and goals

### Pre-step (sequential)

| Step | File | Goal | Success criteria |
|------|------|------|-------------------|
| 0 | [step_00_scope_freeze.md](step_00_scope_freeze.md) | Fix scope, provider names, and target paths for the plan. | SCOPE_FREEZE.md approved; all following steps reference it; no placeholder naming in step files. |

### Documentation and contracts (parallel wave)

| Step | File | Goal | Success criteria |
|------|------|------|-------------------|
| 1 | [step_01_client_standard_document.md](step_01_client_standard_document.md) | Publish normative client standard (mandatory behaviour, contracts, errors). | Document exists in docs; defines required methods, capability flags, error categories, embed contract; referenced by base class step. |
| 2 | [step_02_config_standard_document.md](step_02_config_standard_document.md) | Publish normalized provider client config structure and validation rules. | Document exists; defines provider_clients.* layout, example provider names, validation rules; referenced by schema/validator steps. |

### Base implementation (parallel waves)

| Step | File | Goal | Success criteria |
|------|------|------|-------------------|
| 3 | [step_03_uniform_error_model.md](step_03_uniform_error_model.md) | Introduce shared error classes for provider clients. | Module with TransportError, AuthError, TimeoutError, RateLimitError, ProviderProtocolError, ValidationError (and CapabilityNotSupportedError if used for embed); no pass/NotImplemented in production. |
| 4 | [step_04_abstract_base_class.md](step_04_abstract_base_class.md) | Define abstract base class for all provider clients. | Base class defines validate_config, healthcheck, chat, embed, supports_tools, normalize_response, map_error; capability flags; implements contract from step_01; uses errors from step_03. |
| 5 | [step_05_provider_client_config_schema.md](step_05_provider_client_config_schema.md) | Define schema for provider_clients section. | Schema covers default_provider, providers.<name>.transport/auth/tls/features/limits; usable by validator and generator. |
| 6 | [step_06_provider_client_config_validator.md](step_06_provider_client_config_validator.md) | Implement validator for provider client config. | Validator rejects incomplete/conflicting settings; runs before runtime; step success metric (see step file) green. |
| 7 | [step_07_provider_client_config_generator.md](step_07_provider_client_config_generator.md) | Implement generator for provider client config. | Generator produces valid provider_clients section; step success metric green. |

### Concrete clients and orchestration

| Step | File | Goal | Success criteria |
|------|------|------|-------------------|
| 8 | [step_08_ollama_provider_client.md](step_08_ollama_provider_client.md) | Implement Ollama provider client to shared contract. | Ollama client implements base; transport/auth internal; supports_embeddings and embed per TZ; step success metric green. |
| 9 | [step_09_provider_client_registry.md](step_09_provider_client_registry.md) | Implement registry/factory for provider clients. | Workstation can resolve client by provider name from config; step success metric green. |
| 10 | [step_10_workstation_orchestration_refactor.md](step_10_workstation_orchestration_refactor.md) | Refactor workstation to provider-client-only path; remove direct redis/ollama. | No direct redis/ollama in runtime; model communication only via provider clients and proxy; step success metric green. |

### MCP adapter servers

| Step | File | Goal | Success criteria |
|------|------|------|-------------------|
| 11 | [step_11_database_server_full_surface.md](step_11_database_server_full_surface.md) | Expose full redis tool surface via database-server adapter. | database-server proxy-registered; full command catalog; strict JSON Schema; step success metric green. |
| 12 | [step_12_ollama_server_full_surface.md](step_12_ollama_server_full_surface.md) | Expose full ollama tool surface via ollama-server adapter. | ollama-server proxy-registered; full command catalog; strict JSON Schema; step success metric green. |

### Verification

| Step | File | Goal | Success criteria |
|------|------|------|-------------------|
| 13 | [step_13_integration_tests.md](step_13_integration_tests.md) | Integration tests for no-direct-access, provider parity, proxy registration. | Tests for no-direct-access policy, provider parity via common API, proxy registration and command availability; all pass. |

---

## Parallel execution (waves of 2–4 steps)

Run only steps in the same wave in parallel; next wave starts after the previous wave is fully green.

| Wave | Steps | Description |
|------|-------|-------------|
| 0 | step_00 | Scope freeze (single). |
| 1 | step_01, step_02 | Client standard doc + Config standard doc (2). |
| 2 | step_03, step_05 | Error model + Config schema (2). |
| 3 | step_04, step_06, step_07 | Abstract base + Validator + Generator (3). |
| 4 | step_08, step_09 | Ollama client + Registry (2). |
| 5 | step_10 | Workstation refactor (1). |
| 6 | step_11, step_12 | database-server + ollama-server full surface (2). |
| 7 | step_13 | Integration tests (1). |

Constraints:

- Each step’s **Success metric** is defined in the step file (`atomic/step_NN_<name>.md`); the gate uses those criteria (see QUALITY_GATE § D).
- If any step in a wave fails the gate, resolve before starting the next wave.
- Shared gate and execution protocol: [../QUALITY_GATE.md](../QUALITY_GATE.md).

## Execution protocol

1. Execute in dependency order by waves.
2. For each step: change only the step’s target file(s) and direct tests/artifacts; run checks per QUALITY_GATE (working dir, .venv, code_mapper, black, flake8, mypy, focused tests); verify the **Success metric** from that step’s file.
3. Step-specific success metrics: see the **“Success metric”** section in `atomic/step_NN_<name>.md`.
4. If a requirement is unclear or contradictory: **STOP** and ask for clarification.
