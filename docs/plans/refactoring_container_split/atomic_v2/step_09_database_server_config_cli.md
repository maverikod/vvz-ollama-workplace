# Step 09: Database Server Config CLI

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

## Target file
- `src/database_server/config_cli.py`

## Dependencies
- [`step_08_database_server_config_validator.md`](./step_08_database_server_config_validator.md) (previous step in chain)
- [`NAMING_FREEZE.md`](./NAMING_FREEZE.md) (mandatory naming/source of truth)
- [`ATOMIC_PLAN_V2.md`](./ATOMIC_PLAN_V2.md) (wave and handoff order)
- [`../TRACEABILITY_MATRIX.md`](../TRACEABILITY_MATRIX.md) (requirement mapping)
- [`ADAPTER_BASELINE_SOURCES.md`](./ADAPTER_BASELINE_SOURCES.md) (adapter config contract and base primitives source)
- [`../QUALITY_GATE.md`](../QUALITY_GATE.md)

## Detailed scope
- Full CLI: `generate`, `validate`, `show-schema`, `sample`.
- CLI designed for prompt automation and CI use.
- Startup command/path must call validator before server run.
- On validation errors at startup: write structured error to logs and terminate process.

## Success metric
- DB server configuration lifecycle is operable from terminal only.

## Blocking protocol (mandatory)
- If any requirement is unclear, contradictory, or underspecified: **STOP** implementation.
- Ask a clarifying question and proceed only after explicit clarification.
