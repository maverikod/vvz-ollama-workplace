# Step 00: Naming Freeze and Scope Boundary

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

## Target file
- `docs/plans/refactoring_container_split/atomic_v2/NAMING_FREEZE.md`

## Dependencies
- `../QUALITY_GATE.md`

## Detailed scope
- Fix canonical package names for phase-1 implementation.
- Fix server/client pair list included in this phase.
- Fix publication names for PyPI packages.
- Fix WS contract version identifier and compatibility policy.

## Required output content
- Final names for:
  - `model_workspace_server`
  - `model_workspace_client`
  - `database_server`
  - `database_client`
- Mapping table: internal package name -> PyPI distribution name.
- Explicit list of components out of phase-1 scope.

## Success metric
- Naming document is approved and referenced by all following steps.
- No placeholder naming remains in step files after this step.

## Blocking protocol (mandatory)
- If any requirement is unclear, contradictory, or underspecified: **STOP** implementation.
- Ask a clarifying question and proceed only after explicit clarification.

## Step 00 completion

- **Date:** 2025-03-02
- **Status:** Done
- Naming document `NAMING_FREEZE.md` contains all required output: final package names, PyPI mapping table, WS contract identifier, explicit out-of-scope list; approved as single source of truth.
- All following steps (01–18) reference `NAMING_FREEZE.md`; no placeholder naming remains in step files.
