<!--
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
-->

# Traceability Matrix: CLIENT_UNIFICATION_TZ → Atomic Steps → Verification

## Purpose

- Requirement coverage (FR, AR, deliverables).
- Implementation step links.
- Objective verification commands.

Use together with:

- [`atomic/IMPLEMENTATION_PLAN.md`](./atomic/IMPLEMENTATION_PLAN.md) — step order, goals, success criteria summary, waves
- [`QUALITY_GATE.md`](./QUALITY_GATE.md) — working dir, .venv, exact code_mapper command, pytest focused tests, step closure (success metrics from each step document)
- [`CLIENT_UNIFICATION_TZ.md`](./CLIENT_UNIFICATION_TZ.md) — full requirements; embed contract when unsupported in § Standardized Provider Client Interface

## Step documents (execution plan)

Each step from the matrix has a dedicated description with target file, dependencies, scope, **success metric**, and blocking protocol. Apply QUALITY_GATE to each step using that step’s success metric.

| Step | Document |
|------|----------|
| 0 | [atomic/step_00_scope_freeze.md](./atomic/step_00_scope_freeze.md) |
| 1 | [atomic/step_01_client_standard_document.md](./atomic/step_01_client_standard_document.md) |
| 2 | [atomic/step_02_config_standard_document.md](./atomic/step_02_config_standard_document.md) |
| 3 | [atomic/step_03_uniform_error_model.md](./atomic/step_03_uniform_error_model.md) |
| 4 | [atomic/step_04_abstract_base_class.md](./atomic/step_04_abstract_base_class.md) |
| 5 | [atomic/step_05_provider_client_config_schema.md](./atomic/step_05_provider_client_config_schema.md) |
| 6 | [atomic/step_06_provider_client_config_validator.md](./atomic/step_06_provider_client_config_validator.md) |
| 7 | [atomic/step_07_provider_client_config_generator.md](./atomic/step_07_provider_client_config_generator.md) |
| 8 | [atomic/step_08_ollama_provider_client.md](./atomic/step_08_ollama_provider_client.md) |
| 9 | [atomic/step_09_provider_client_registry.md](./atomic/step_09_provider_client_registry.md) |
| 10 | [atomic/step_10_workstation_orchestration_refactor.md](./atomic/step_10_workstation_orchestration_refactor.md) |
| 11 | [atomic/step_11_database_server_full_surface.md](./atomic/step_11_database_server_full_surface.md) |
| 12 | [atomic/step_12_ollama_server_full_surface.md](./atomic/step_12_ollama_server_full_surface.md) |
| 13 | [atomic/step_13_integration_tests.md](./atomic/step_13_integration_tests.md) |

## Functional requirements

| Req ID | Requirement | Covered by steps | Verification (objective) | Status |
|--------|-------------|------------------|---------------------------|--------|
| FR-1 | Full MCP control of redis and ollama | `step_11`, `step_12`, `step_13` | No direct workstation→redis/ollama; `database-server` and `ollama-server` proxy-registered; command catalogs published; integration tests confirm tool-only access | Mapped |
| FR-2 | Provider client unification | `step_04`, `step_08`, `step_09`, `step_10` | All model communication via provider clients; Ollama as first-class provider; transport/auth internal to clients | Mapped |
| FR-3 | Common workstation client API | `step_01`, `step_04`, `step_08`, `step_10` | Single uniform API in workstation terms; translation inside clients; orchestration provider-agnostic | Mapped |
| FR-4 | Standard and abstract base class | `step_01`, `step_03`, `step_04`, `step_08` | Normative client standard doc; shared error model; abstract base with required methods; all clients implement contract | Mapped |
| FR-5 | Standardized provider client config | `step_02`, `step_05`, `step_06`, `step_07` | Normalized `provider_clients` section; schema/validator/generator; validation rejects invalid startup | Mapped |

## Architecture requirements

| Req ID | Requirement | Covered by steps | Verification (objective) | Status |
|--------|-------------|------------------|---------------------------|--------|
| AR-1 | Access path policy (allowed/forbidden) | `step_10`, `step_11`, `step_12`, `step_13` | Runtime: only `workstation→provider_client→provider` and `workstation→ProxyClient→call_server→adapter→backend`; no direct redis/ollama | Mapped |
| AR-2 | MCP tool surface (catalogs, JSON Schema, mTLS) | `step_11`, `step_12`, `step_13` | Full command catalogs; strict JSON Schema params; tool-level auth/TLS aligned with proxy mTLS | Mapped |
| AR-3 | Uniform error model | `step_01`, `step_03`, `step_04`, `step_08` | Shared categories: TransportError, AuthError, TimeoutError, RateLimitError, ProviderProtocolError, ValidationError; clients use map_error | Mapped |

## Implementation deliverables

| Deliverable | Covered by steps | Verification | Status |
|-------------|------------------|--------------|--------|
| 1. Client standard document | `step_01` | Document exists; normative rules; referenced by base class and steps | Mapped |
| 2. Abstract base class | `step_04` | Base class defines validate_config, healthcheck, chat, embed (mandatory; see TZ embed contract when unsupported), supports_tools, normalize_response, map_error; capability flags | Mapped |
| 3. Concrete clients migrated | `step_08`, `step_09`, `step_10` | At least Ollama client; registry; workstation uses only clients | Mapped |
| 4. Workstation orchestration refactor | `step_10` | No direct redis/ollama; provider-client-only path | Mapped |
| 5. MCP adapter servers (redis, ollama) | `step_11`, `step_12` | database-server, ollama-server proxy-registered; full tool surface | Mapped |
| 6. Config schema/generator/validator | `step_05`, `step_06`, `step_07` | provider_clients section; validation blocks invalid startup | Mapped |
| 7. Integration tests | `step_13` | no-direct-access policy; provider parity; proxy registration and command availability | Mapped |

## Verification command templates

### Shared quality gate

1. `code_mapper -r /home/vasilyvz/projects/ollama`
2. `black /home/vasilyvz/projects/ollama`
3. `flake8 /home/vasilyvz/projects/ollama`
4. `mypy /home/vasilyvz/projects/ollama`

### Provider client config

- Validate provider_clients section (validator CLI or API).
- Generate sample config (generator CLI or API).
- Workstation startup fails when provider client config invalid.

### No-direct-access policy

- Grep/static check: no direct redis/ollama client usage in workstation runtime path.
- Integration test: disable proxy → model cannot access redis/ollama.

### Proxy and adapters

- `list_servers()` shows `database-server`, `ollama-server`.
- Command catalogs for both; help returns strict JSON Schema.
- Integration test: call_server(database-server, ...), call_server(ollama-server, ...) succeed with real backend.
