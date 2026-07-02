# `docs/standards/` — Machine Standards Index

All standards are YAML with a mandatory `meta:` block. Agents read a standard
when `docs/agent-ref/roles/tooling.yaml: triggers` or a role's `standards:`
list names it.

## Codex Tooling Manuals

| File | Governs |
|------|---------|
| `codex_search_standard.yaml` | Searching and code analysis in this repository. |
| `codex_editing_standard.yaml` | Editing constraints and repository conventions. |
| `codex_terminal_standard.yaml` | Terminal commands, builds, tests, and verification. |

## Planning Stack

| File | Governs |
|------|---------|
| `plan_standard_machine.yaml` | Five-level plan hierarchy and cascade changes. |
| `tactical_step_creation_standard.yaml` | Tactical step authoring. |
| `atomic_step_creation_standard.yaml` | Atomic step authoring: one file, complete prompt. |
| `hrs_mrs_gs_consistency_verification_standard.yaml` | Consistency verification across upper planning levels. |

