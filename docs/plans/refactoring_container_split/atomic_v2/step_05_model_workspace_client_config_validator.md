# Step 05: Model Workspace Client Config Validator

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

## Target file
- `src/model_workspace_client/config_validator.py`

## Dependencies
- [`step_04_model_workspace_client_config_generator.md`](./step_04_model_workspace_client_config_generator.md) (previous step in chain)
- [`NAMING_FREEZE.md`](./NAMING_FREEZE.md) (mandatory naming/source of truth)
- [`ATOMIC_PLAN_V2.md`](./ATOMIC_PLAN_V2.md) (wave and handoff order)
- [`../TRACEABILITY_MATRIX.md`](../TRACEABILITY_MATRIX.md) (requirement mapping)
- [`ADAPTER_BASELINE_SOURCES.md`](./ADAPTER_BASELINE_SOURCES.md) (adapter config contract and base primitives source)
- [`../QUALITY_GATE.md`](../QUALITY_GATE.md)

## Detailed scope
- Validate endpoint, WS options, auth headers/tokens/certs, retry policy.
- Detect invalid combinations before runtime connection attempt.
- Build validator on adapter config files and adapter base validator primitives from [`ADAPTER_BASELINE_SOURCES.md`](./ADAPTER_BASELINE_SOURCES.md).
- Validator must run on client init/start; on validation errors: return error and raise exception.

## Success metric
- Validator blocks malformed client config with deterministic error classification.

## Blocking protocol (mandatory)
- If any requirement is unclear, contradictory, or underspecified: **STOP** implementation.
- Ask a clarifying question and proceed only after explicit clarification.
