<!--
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
-->

# Parallel Execution Chains (Atomic Plan)

Source plan: [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md).
Shared gate: [../QUALITY_GATE.md](../QUALITY_GATE.md).

This file provides explicit step chains and parallel bundles for execution handoff.

## Step count note

- This file is for **provider_client_unification** only. Its atomic plan is
  `step_00 ... step_13` (14 steps total including step_00).
- The separate 18-step plan is:
  `docs/plans/refactoring_container_split/atomic_v2/ATOMIC_PLAN_V2.md`
  (`step_00 ... step_18`).

## Parallel bundles (can run concurrently inside bundle)

| Bundle | Steps | Parallelism | Preconditions | Next gate |
|--------|-------|-------------|---------------|-----------|
| B0 | `step_00` | 1 | none | B1 |
| B1 | `step_01`, `step_02` | 2 | B0 green | B2 |
| B2 | `step_03`, `step_05` | 2 | B1 green | B3 |
| B3 | `step_04`, `step_06`, `step_07` | 3 | B2 green | B4 |
| B4 | `step_08`, `step_09` | 2 | B3 green | B5 |
| B5 | `step_10` | 1 | B4 green | B6 |
| B6 | `step_11`, `step_12` | 2 | B5 green | B7 |
| B7 | `step_13` | 1 | B6 green | done |

## Dependency chains (worker-oriented view)

- **Chain A (client contract):** `step_00 -> step_01 -> step_03 -> step_04 -> step_08 -> step_10 -> step_13`
- **Chain B (config path):** `step_00 -> step_02 -> step_05 -> step_06 -> step_09 -> step_10 -> step_13`
- **Chain C (config generation path):** `step_00 -> step_02 -> step_05 -> step_07 -> step_09 -> step_10 -> step_13`
- **Chain D (database adapter surface):** `step_00 -> step_10 -> step_11 -> step_13`
- **Chain E (ollama adapter surface):** `step_00 -> step_10 -> step_12 -> step_13`

## Execution rules

- Run only steps from the same bundle in parallel.
- Start next bundle only when all steps in current bundle are green under QUALITY_GATE.
- For each step, use that step file `step_NN_*.md` as source of success metrics.
- If any step fails gate checks, pause bundle and resolve before continuing.
