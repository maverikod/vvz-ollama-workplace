<!--
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
-->

# Step 00: Scope Freeze and Boundary

## Target file

- `docs/plans/provider_client_unification/atomic/SCOPE_FREEZE.md`

## Dependencies

- [../QUALITY_GATE.md](../QUALITY_GATE.md)
- [../CLIENT_UNIFICATION_TZ.md](../CLIENT_UNIFICATION_TZ.md)

## Detailed scope

- Fix canonical provider names and target server IDs for this plan (`database-server`, `ollama-server`).
- Fix list of in-scope provider clients (at least Ollama; optional others for phase 1).
- Fix target paths for new modules (e.g. `src/ollama_workstation/provider_errors.py`, `provider_client_base.py`, config schema location).
- Explicit list of components or code paths out of scope for this plan.
- Reference to embed contract (method mandatory; unsupported = flag + defined error) from TZ.
- Explicitly lock Greenfield policy from TZ: no legacy direct-access runtime paths and no long-term compatibility shims.

## Success metric

- SCOPE_FREEZE.md is written and contains: provider names, server IDs, target file paths, out-of-scope list.
- All following steps (01–13) reference SCOPE_FREEZE.md where applicable; no placeholder naming remains in step files after this step.

## Blocking protocol (mandatory)

- If any requirement is unclear, contradictory, or underspecified: **STOP** implementation.
- Ask a clarifying question and proceed only after explicit clarification.
