# Step 08: Database Server Config Validator

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

## Target file
- `src/database_server/config_validator.py`

## Dependencies
- [`step_07_database_server_config_generator.md`](./step_07_database_server_config_generator.md) (previous step in chain)
- [`NAMING_FREEZE.md`](./NAMING_FREEZE.md) (mandatory naming/source of truth)
- [`ATOMIC_PLAN_V2.md`](./ATOMIC_PLAN_V2.md) (wave and handoff order)
- [`../TRACEABILITY_MATRIX.md`](../TRACEABILITY_MATRIX.md) (requirement mapping)
- [`ADAPTER_BASELINE_SOURCES.md`](./ADAPTER_BASELINE_SOURCES.md) (adapter config contract and base primitives source)
- [`../QUALITY_GATE.md`](../QUALITY_GATE.md)

## Detailed scope
- Validate DB server config: endpoints, auth/TLS, persistence and limits.
- Validate compatibility with expected client contract.
- Build validator on adapter config files and adapter base validator primitives from [`ADAPTER_BASELINE_SOURCES.md`](./ADAPTER_BASELINE_SOURCES.md).
- Validator must run on server startup; on validation errors: log diagnostics and stop startup.

## Success metric
- Invalid DB server config is blocked with explicit field-level diagnostics.

## Blocking protocol (mandatory)
- If any requirement is unclear, contradictory, or underspecified: **STOP** implementation.
- Ask a clarifying question and proceed only after explicit clarification.
