# Step 11: Database Client Config Validator

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

## Target file
- `src/database_client/config_validator.py`

## Dependencies
- [`step_10_database_client_config_generator.md`](./step_10_database_client_config_generator.md) (previous step in chain)
- [`NAMING_FREEZE.md`](./NAMING_FREEZE.md) (mandatory naming/source of truth)
- [`ATOMIC_PLAN_V2.md`](./ATOMIC_PLAN_V2.md) (wave and handoff order)
- [`../TRACEABILITY_MATRIX.md`](../TRACEABILITY_MATRIX.md) (requirement mapping)
- [`ADAPTER_BASELINE_SOURCES.md`](./ADAPTER_BASELINE_SOURCES.md) (adapter config contract and base primitives source)
- [`../QUALITY_GATE.md`](../QUALITY_GATE.md)

## Detailed scope
- Validate DB client config and transport/auth/security consistency.
- Detect incompatible settings versus DB server contract.
- Build validator on adapter config files and adapter base validator primitives from [`ADAPTER_BASELINE_SOURCES.md`](./ADAPTER_BASELINE_SOURCES.md).
- Validator must run on client init/start; on validation errors: return error and raise exception.

## Success metric
- Validator deterministically rejects invalid DB client config before runtime.

## Blocking protocol (mandatory)
- If any requirement is unclear, contradictory, or underspecified: **STOP** implementation.
- Ask a clarifying question and proceed only after explicit clarification.
