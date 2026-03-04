<!--
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
-->

# Provider Client Unification — Plan

Execution plan for **Provider Client Unification and MCP Control** ([CLIENT_UNIFICATION_TZ.md](CLIENT_UNIFICATION_TZ.md)).

## Plan structure

| Document | Purpose |
|----------|---------|
| [CLIENT_UNIFICATION_TZ.md](CLIENT_UNIFICATION_TZ.md) | Technical assignment: FR/AR, interface, config, acceptance criteria |
| [QUALITY_GATE.md](QUALITY_GATE.md) | Mandatory gate for each step: environment, commands, tests, step closure |
| [TRACEABILITY_MATRIX.md](TRACEABILITY_MATRIX.md) | FR/AR/deliverables → steps → verification |
| **[atomic/IMPLEMENTATION_PLAN.md](atomic/IMPLEMENTATION_PLAN.md)** | **Step order, goals, success criteria summary, parallel waves** |
| **atomic/step_00_scope_freeze.md** … **atomic/step_13_integration_tests.md** | **Per-step description: target file, dependencies, scope, success metric, blocking protocol** |

The gate in QUALITY_GATE.md applies to **each step** of this plan. Step list and step-specific success metrics are defined in:

- **atomic/IMPLEMENTATION_PLAN.md** — table of steps with short goals and success criteria
- **atomic/step_NN_<name>.md** — full description and **Success metric** section for step NN

So the plan is fully executable: for any step (01 … 13), open the corresponding `atomic/step_NN_*.md` to see what to do and what “green” means for that step.
