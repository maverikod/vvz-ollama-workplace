# Step 04: Model Workspace Client Config Generator

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

## Target file
- `src/model_workspace_client/config_generator.py`

## Dependencies
- [`step_03_model_workspace_server_config_cli.md`](./step_03_model_workspace_server_config_cli.md) (previous step in chain)
- [`NAMING_FREEZE.md`](./NAMING_FREEZE.md) (mandatory naming/source of truth)
- [`ATOMIC_PLAN_V2.md`](./ATOMIC_PLAN_V2.md) (wave and handoff order)
- [`../TRACEABILITY_MATRIX.md`](../TRACEABILITY_MATRIX.md) (requirement mapping)
- [`ADAPTER_BASELINE_SOURCES.md`](./ADAPTER_BASELINE_SOURCES.md) (adapter config contract and base primitives source)
- [`../QUALITY_GATE.md`](../QUALITY_GATE.md)

## Detailed scope
- Generate client config for connecting to model workspace server.
- Include WS endpoint, auth/TLS fields, retries, timeouts, observability options.
- Ensure generated config can be used as independent package runtime input.
- Build generator on adapter config files and adapter base generator primitives from [`ADAPTER_BASELINE_SOURCES.md`](./ADAPTER_BASELINE_SOURCES.md).
- Output must remain compatible with one adapter config contract.

## Success metric
- Generated config is directly consumable by model workspace client package.

## Blocking protocol (mandatory)
- If any requirement is unclear, contradictory, or underspecified: **STOP** implementation.
- Ask a clarifying question and proceed only after explicit clarification.
