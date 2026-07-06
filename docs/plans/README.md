# `docs/plans/` — development plan tree

Format is governed by `docs/standards/plan_standard_machine.yaml` (hierarchy and
required fields), `tactical_step_creation_standard.yaml` and
`atomic_step_creation_standard.yaml` (authoring levels 4–5).

Directory convention:

```text
docs/plans/
  source_spec.md                  # HRS — human-readable source spec
  spec.yaml                       # MRS — machine spec (concepts, invariants)
  gs_concept_matrix.yaml          # concept coverage matrices
  object_matrix.yaml              # object/work-axis matrix
  G-001-<slug>/                   # GS — global step
    README.yaml
    T-001-<slug>/                 # TS — tactical step
      README.yaml
      atomic_steps/
        A-001-<slug>.yaml         # AS — atomic step: one file, self-sufficient prompt
        A-002-<slug>.yaml
  G-002-<slug>/
  ...
```

Rules:
- IDs `G-NNN` / `T-NNN` / `A-NNN` are zero-padded, stable, never reused;
- all changes flow top-down via the cascade procedure of the plan standard;
- an atomic step targets exactly one file and inlines everything its coder needs.

## Plans registry

| Plan | Status | Notes |
| ---- | ------ | ----- |
| [workspace_orchestration_refactoring/source_spec.md](workspace_orchestration_refactoring/source_spec.md) | **Active** (HRS draft) | Canonical spec. Refactors mwps into an integration/orchestration layer: LLM provider access delegated to model-access-core, local model runtime to lmrs, search/vectorization to svo/embed/doc-store. |

Removed plans (history in git): `refactoring_adapter_structure/` and `refactoring_comprehensive_analysis/` — deleted 2026-07-05 as superseded by the active plan.
