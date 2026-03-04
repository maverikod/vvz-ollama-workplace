# Step 06: Model Workspace Client Config CLI

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

## Target file
- `src/model_workspace_client/config_cli.py`

## Dependencies
- [`step_05_model_workspace_client_config_validator.md`](./step_05_model_workspace_client_config_validator.md) (previous step in chain)
- [`NAMING_FREEZE.md`](./NAMING_FREEZE.md) (mandatory naming/source of truth)
- [`ATOMIC_PLAN_V2.md`](./ATOMIC_PLAN_V2.md) (wave and handoff order)
- [`../TRACEABILITY_MATRIX.md`](../TRACEABILITY_MATRIX.md) (requirement mapping)
- [`ADAPTER_BASELINE_SOURCES.md`](./ADAPTER_BASELINE_SOURCES.md) (adapter config contract and base primitives source)
- [`../QUALITY_GATE.md`](../QUALITY_GATE.md)

## Detailed scope
- Full CLI: `generate`, `validate`, `show-schema`, `test-connection`.
- `test-connection` must check real WS handshake in safe mode.
- Client startup/init path must call validator before first network operation.
- On validation errors at startup/init: return error and raise exception.

## Success metric
- Client config lifecycle is fully operable from prompt/terminal commands.

## Blocking protocol (mandatory)
- If any requirement is unclear, contradictory, or underspecified: **STOP** implementation.
- Ask a clarifying question and proceed only after explicit clarification.
