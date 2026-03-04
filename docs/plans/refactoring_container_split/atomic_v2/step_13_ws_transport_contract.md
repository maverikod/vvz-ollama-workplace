# Step 13: WS Transport Contract (Pairs + Adapter)

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

## Target file
- `src/ollama_workstation/proxy_client.py`

## Dependencies
- [`step_12_database_client_config_cli.md`](./step_12_database_client_config_cli.md) (previous step in chain)
- [`NAMING_FREEZE.md`](./NAMING_FREEZE.md) (mandatory naming/source of truth)
- [`ATOMIC_PLAN_V2.md`](./ATOMIC_PLAN_V2.md) (wave and handoff order)
- [`../TRACEABILITY_MATRIX.md`](../TRACEABILITY_MATRIX.md) (verification mapping for R4/R10)
- [`../QUALITY_GATE.md`](../QUALITY_GATE.md)

## Detailed scope
- Enforce WS-first path where adapter supports WS.
- Document and implement controlled fallback policy.
- Ensure both model-workspace and database client pairs use aligned WS contract.

## Success metric
- Integration evidence confirms active WS path for both pair types, where "integration evidence" means:
  - test execution artifact (pytest output) from the integration scenario that covers both pair types;
  - runtime logs/artifacts showing WS transport path used by model-workspace pair and database pair;
  - explicit fallback behavior evidence: fallback is used only under configured fallback conditions and is logged.

## Blocking protocol (mandatory)
- If any requirement is unclear, contradictory, or underspecified: **STOP** implementation.
- Ask a clarifying question and proceed only after explicit clarification.
