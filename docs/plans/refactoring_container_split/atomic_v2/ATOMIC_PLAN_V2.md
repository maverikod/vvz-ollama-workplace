# Atomic Plan V2 (Cursor Auto Ready, Detailed)

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

This plan is the strict execution variant: **one step = one target code file**.
Primary architecture focus:
- **Model Workspace pair** (`model_workspace_server` <-> `model_workspace_client`)
- **Database pair** (`database_server` <-> `database_client`)

Use shared gate:
- `../QUALITY_GATE.md`
- Every step includes mandatory blocking protocol: if unclear, stop and ask.

## Step order

### Naming freeze (mandatory pre-step)
0. `step_00_naming_freeze.md`

### Model Workspace pair
1. `step_01_model_workspace_server_config_generator.md`
2. `step_02_model_workspace_server_config_validator.md`
3. `step_03_model_workspace_server_config_cli.md`
4. `step_04_model_workspace_client_config_generator.md`
5. `step_05_model_workspace_client_config_validator.md`
6. `step_06_model_workspace_client_config_cli.md`

### Database pair
7. `step_07_database_server_config_generator.md`
8. `step_08_database_server_config_validator.md`
9. `step_09_database_server_config_cli.md`
10. `step_10_database_client_config_generator.md`
11. `step_11_database_client_config_validator.md`
12. `step_12_database_client_config_cli.md`

### Cross-cutting platform
13. `step_13_ws_transport_contract.md`
14. `step_14_registration_and_command_catalog.md`
15. `step_15_container_runtime_contract.md`
16. `step_16_client_packaging_pypi.md`
17. `step_17_real_integration_no_mocks.md`
18. `step_18_final_real_ws_gate.md`

## Parallel execution sequence (up to 4 models)

Use 4 execution models (workers) maximum. Run only inside the same wave in parallel.

- Wave 0 (sequential, single): `step_00`
- Wave 1 (parallel x4): `step_01`, `step_04`, `step_07`, `step_10`
- Wave 2 (parallel x4): `step_02`, `step_05`, `step_08`, `step_11`
- Wave 3 (parallel x4): `step_03`, `step_06`, `step_09`, `step_12`
- Wave 4 (sequential, single): `step_13`
- Wave 5 (parallel x3): `step_14`, `step_15`, `step_16`
- Wave 6 (sequential, single): `step_17`
- Wave 7 (sequential, single): `step_18`

Parallelization constraints:
- Next wave starts only after full green status of the previous wave.
- Inside each wave, each step still follows one-target-file rule.
- If any step in wave fails gate, stop the whole wave and resolve before proceeding.

## Global acceptance

- Step 00 completed and approved.
- Every step passes its local success metric.
- Shared gate passes on each step.
- Final real WS gate passes with no mocks.
- No unresolved contradiction between model-workspace and database pair contracts.
- For every server/client pair, config generator and validator are built on adapter config files and adapter base generator/validator primitives (no parallel config format).
- Validator is mandatory on startup:
  - server startup: on validation errors write diagnostics to logs and stop process;
  - client startup/init: return validation error and raise exception.

## Execution protocol (model handoff)

- Execute in dependency order by waves (see "Parallel execution sequence").
- For each step, modify only the step target file and direct required tests/artifacts.
- Before any new implementation in a step: check `code_analysis/*` and reuse existing adapter primitives where possible.
- After each step:
  1. run `code_mapper -r /home/vasilyvz/projects/ollama`;
  2. run `black`, `flake8`, `mypy`;
  3. run focused tests for changed behavior;
  4. verify step success metric from the step file.
- Do not proceed to next step until current step passes all checks.
- If requirement is unclear/contradictory/underspecified: **STOP** and ask clarifying question.

## Release readiness status

- Status: **Ready for execution transfer**.
- Preconditions are fixed in `NAMING_FREEZE.md` and mapped in `TRACEABILITY_MATRIX.md`.
- Shared mandatory gate: `../QUALITY_GATE.md`.
