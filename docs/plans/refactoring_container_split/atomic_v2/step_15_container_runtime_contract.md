# Step 15: Container Runtime Contract

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

## Target file
- `docker/build_and_run.sh`

## Dependencies
- [`step_14_registration_and_command_catalog.md`](./step_14_registration_and_command_catalog.md) (previous step in chain)
- [`NAMING_FREEZE.md`](./NAMING_FREEZE.md) (mandatory naming/source of truth)
- [`ATOMIC_PLAN_V2.md`](./ATOMIC_PLAN_V2.md) (wave and handoff order)
- [`../TRACEABILITY_MATRIX.md`](../TRACEABILITY_MATRIX.md) (verification mapping for runtime contract)
- [`../QUALITY_GATE.md`](../QUALITY_GATE.md)

## Detailed scope
- Enforce mandatory mounts: config, logs, model cache, data.
- Enforce user mapping `1000:1000`.
- Enforce auto-attach to `smart-assistant`.

## Success metric
- Runtime inspection confirms mounts/user/network contract on running containers.
- Runtime inspection procedure (mandatory):
  - use `docker ps` to list required running containers;
  - use `docker inspect <container>` and verify:
    - mounts contain required config/logs/cache/model-data paths;
    - `Config.User` or effective runtime user is `1000:1000`;
    - container is attached to network `smart-assistant`.
- Success is green only when all required containers pass all three checks (mounts + user + network); any mismatch means step failure.

## Blocking protocol (mandatory)
- If any requirement is unclear, contradictory, or underspecified: **STOP** implementation.
- Ask a clarifying question and proceed only after explicit clarification.
