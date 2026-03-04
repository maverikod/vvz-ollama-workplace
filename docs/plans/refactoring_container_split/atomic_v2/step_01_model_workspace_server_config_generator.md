# Step 01: Model Workspace Server Config Generator

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

## Target file
- `src/model_workspace_server/config_generator.py`

## Dependencies
- [`step_00_naming_freeze.md`](./step_00_naming_freeze.md) (must be completed first)
- [`NAMING_FREEZE.md`](./NAMING_FREEZE.md) (mandatory naming/source of truth)
- [`ATOMIC_PLAN_V2.md`](./ATOMIC_PLAN_V2.md) (wave and handoff order)
- [`../TRACEABILITY_MATRIX.md`](../TRACEABILITY_MATRIX.md) (requirement mapping)
- [`ADAPTER_BASELINE_SOURCES.md`](./ADAPTER_BASELINE_SOURCES.md) (adapter config contract and base primitives source)
- [`../QUALITY_GATE.md`](../QUALITY_GATE.md)

## Detailed scope
- Generate server config for model workspace service.
- Include transport (`ws`, fallback policy), security, limits, logs paths, runtime identity.
- Support prompt-driven generation (args/env/template merging).
- Build generator on adapter config files and adapter base generator primitives from [`ADAPTER_BASELINE_SOURCES.md`](./ADAPTER_BASELINE_SOURCES.md).
- Output must be a single adapter config consumed by adapter runtime.

## Success metric
- One command generates valid config for model workspace server with WS-ready section.

## Blocking protocol (mandatory)
- If any requirement is unclear, contradictory, or underspecified: **STOP** implementation.
- Ask a clarifying question and proceed only after explicit clarification.
