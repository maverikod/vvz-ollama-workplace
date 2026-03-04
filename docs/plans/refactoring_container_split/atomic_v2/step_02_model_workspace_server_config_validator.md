# Step 02: Model Workspace Server Config Validator

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

## Target file
- `src/model_workspace_server/config_validator.py`

## Dependencies
- [`step_01_model_workspace_server_config_generator.md`](./step_01_model_workspace_server_config_generator.md) (previous step in chain)
- [`NAMING_FREEZE.md`](./NAMING_FREEZE.md) (mandatory naming/source of truth)
- [`ATOMIC_PLAN_V2.md`](./ATOMIC_PLAN_V2.md) (wave and handoff order)
- [`../TRACEABILITY_MATRIX.md`](../TRACEABILITY_MATRIX.md) (requirement mapping)
- [`ADAPTER_BASELINE_SOURCES.md`](./ADAPTER_BASELINE_SOURCES.md) (adapter config contract and base primitives source)
- [`../QUALITY_GATE.md`](../QUALITY_GATE.md)

## Detailed scope
- Validate config schema, required fields, constraints, file paths and transport consistency.
- Validate WS + TLS coherence and operational defaults.
- Return machine-readable and user-readable diagnostics.
- Build validator on adapter config files and adapter base validator primitives from [`ADAPTER_BASELINE_SOURCES.md`](./ADAPTER_BASELINE_SOURCES.md).
- Validator must run on server startup; on validation errors: log diagnostics and stop startup.

## Success metric
- Invalid config is rejected with exact field path and clear remediation message.

## Blocking protocol (mandatory)
- If any requirement is unclear, contradictory, or underspecified: **STOP** implementation.
- Ask a clarifying question and proceed only after explicit clarification.
