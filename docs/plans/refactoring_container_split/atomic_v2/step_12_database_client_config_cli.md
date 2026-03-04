# Step 12: Database Client Config CLI

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

## Target file
- `src/database_client/config_cli.py`

## Dependencies
- [`step_11_database_client_config_validator.md`](./step_11_database_client_config_validator.md) (previous step in chain)
- [`NAMING_FREEZE.md`](./NAMING_FREEZE.md) (mandatory naming/source of truth)
- [`ATOMIC_PLAN_V2.md`](./ATOMIC_PLAN_V2.md) (wave and handoff order)
- [`../TRACEABILITY_MATRIX.md`](../TRACEABILITY_MATRIX.md) (requirement mapping)
- [`ADAPTER_BASELINE_SOURCES.md`](./ADAPTER_BASELINE_SOURCES.md) (adapter config contract and base primitives source)
- [`../QUALITY_GATE.md`](../QUALITY_GATE.md)

## Detailed scope
- Full CLI: `generate`, `validate`, `show-schema`, `test-connection`.
- Connection test must report transport/auth failures clearly.
- Client startup/init path must call validator before first network operation.
- On validation errors at startup/init: return error and raise exception.

## Success metric
- DB client config can be generated and preflight-tested from prompt/terminal.

## Blocking protocol (mandatory)
- If any requirement is unclear, contradictory, or underspecified: **STOP** implementation.
- Ask a clarifying question and proceed only after explicit clarification.
