# Step 07: Database Server Config Generator

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

## Target file
- `src/database_server/config_generator.py`

## Dependencies
- [`step_06_model_workspace_client_config_cli.md`](./step_06_model_workspace_client_config_cli.md) (previous step in chain)
- [`NAMING_FREEZE.md`](./NAMING_FREEZE.md) (mandatory naming/source of truth)
- [`ATOMIC_PLAN_V2.md`](./ATOMIC_PLAN_V2.md) (wave and handoff order)
- [`../TRACEABILITY_MATRIX.md`](../TRACEABILITY_MATRIX.md) (requirement mapping)
- [`ADAPTER_BASELINE_SOURCES.md`](./ADAPTER_BASELINE_SOURCES.md) (adapter config contract and base primitives source)
- [`../QUALITY_GATE.md`](../QUALITY_GATE.md)

## Detailed scope
- Generate DB server config for networked service role.
- Include transport/auth/storage settings and mount paths.
- Support prompt-based config creation.
- Build generator on adapter config files and adapter base generator primitives from [`ADAPTER_BASELINE_SOURCES.md`](./ADAPTER_BASELINE_SOURCES.md).
- Output must be a single adapter config consumed by adapter runtime.

## Success metric
- Database server config can be generated non-interactively for real deployment.

## Blocking protocol (mandatory)
- If any requirement is unclear, contradictory, or underspecified: **STOP** implementation.
- Ask a clarifying question and proceed only after explicit clarification.
