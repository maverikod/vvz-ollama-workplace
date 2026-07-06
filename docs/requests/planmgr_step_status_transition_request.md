# Feature Request: step lifecycle status transition (single + bulk freeze) for plan-manager

**Author:** Vasiliy Zdanovskiy
**email:** vasilyvz@gmail.com
**Date:** 2026-07-07
**Requesting project:** mwps (Agent Workstation)
**Requesting plan:** `workspace_orchestration_refactoring` (uuid `e271ef77-0e62-4450-8bfa-f253659a0534`)
**planmgr version observed:** 0.1.4 (build 2026-07-06T21:09:20Z)
**Severity:** interface gap — blocks execution of a committed, gate-green plan

## Table of contents

1. Problem statement
2. Evidence (2026-07-07)
3. Why this blocks the workflow
4. Proposed command(s)
5. Interface sketch
6. Legal transition model
7. Acceptance criteria
8. Non-goals
9. Open questions
10. Related requests

## 1. Problem statement

A plan authored through `step_create`/`step_update` lands every GS/TS/AS at lifecycle status
`draft` (the authoritative `step_get.data.status`). `cascade_commit` freezes the **revision**
(advances head, gate goes green) but does **not** transition the **step status** — steps remain
`draft` after commit.

`plan_prompt_chain` (0.1.4) deliberately compiles only steps whose status is in
`{frozen, ready_for_review}` — its `include_statuses` parameter rejects `draft` outright
(`must be one of ['frozen','ready_for_review']`). This is the correct gate: draft steps must not be
emitted as executable prompts.

The result is a deadlock: a fully authored, mechanically-green, committed plan yields an **empty**
prompt-chain corpus, and there is **no exposed command to move a step out of `draft`**. The `step`
family is `create / get / update / delete / move / list / runtime_get / runtime_report /
runtime_list`; none transition lifecycle status. `step_update` explicitly does not accept a `status`
parameter (allowed: `plan, step_id, fields, concepts, cascade_uuid, project_id`). The `info`
glossary references a "review/freeze flow" and a "command transition model", but no command in the
public surface realizes the `draft → ready_for_review → frozen` transition.

## 2. Evidence (2026-07-07)

Against plan `e271ef77-…`, committed head `8ea27aaf-b9d5-4259-8922-240763bc3d3b` (109 HRS labels,
45 concepts, 72 relations, 9 GS, all TS/AS, `plan_validate` green on every check incl. `coverage.*`):

1. `plan_prompt_chain(scope="G-006", role="coder")` → success, but
   `counts = {hrs:0, mrs:0, gs:0, ts:0, as:0, tool_instructions:1, assembly:0}`, `waves:[]`,
   `assembly:[]`. Only the fixed `tool_instructions` block is emitted.
2. `plan_prompt_chain(..., include_statuses=["draft","ready_for_review","frozen"])` →
   `-32602 … include_statuses[0] must be one of ['frozen','ready_for_review'], got 'draft'`.
3. `step_get("G-006/T-001/A-001")` → `data.status == "draft"` (all authored steps are `draft`).
4. `step_update(..., status="ready_for_review")` → `-32602 Invalid parameters: status`.
   `step_update(..., fields={status:"ready_for_review"})` → accepted, but stored only as an inert
   key inside `fields`; authoritative `data.status` stayed `draft`. So `fields.status` is a no-op.

There is no host-independent, MCP-only path to make an authored plan executable.

## 3. Why this blocks the workflow

mwps executes a plan by calling `plan_prompt_chain` on a committed green revision and running the
returned coder corpus on small models. That corpus is empty until steps reach `ready_for_review`/
`frozen`. Freezing ~200 steps one-by-one is not viable even if a single-step verb existed, because
each `step_update` currently advances a new revision — a bulk, scope-level transition is required.
Freezing the authored steps is also the intended **governance milestone** (the point a human /
Conscience review gates before the plan is published for execution), so the transition should be an
explicit, auditable operation, not a silent side effect.

## 4. Proposed command(s)

Add an explicit lifecycle-transition command, scope-aware so a whole plan or subtree can be
transitioned in one call:

- **`step_transition`** — move one step, or every step under a scope, to a target status, subject to
  the legal transition model (§6) and a green mechanical gate for that scope.

Single-step and bulk are the same command distinguished by `scope` vs `step_id`. A dry-run mode
reports what would transition without mutating.

## 5. Interface sketch

```
step_transition(
  plan:            string,                 # plan name or uuid
  to_status:       "ready_for_review" | "frozen" | "draft",   # target lifecycle status
  step_id:         string | omitted,       # single step by path/uuid  (mutually exclusive with scope)
  scope:           "whole_plan" | "G-NNN" | "G-NNN/T-NNN" | omitted,  # bulk transition
  require_green:   bool = true,            # refuse to freeze a scope whose mechanical gate is red
  dry_run:         bool = false,           # report the transition set without mutating
  cascade_uuid:    string | omitted        # required only when transitioning frozen steps (see §6)
) -> {
  transitioned: [ { step_id, from, to } ],
  skipped:      [ { step_id, from, reason } ],   # e.g. already at target, illegal transition
  gate:         { green: bool, scope: "..." },
  revision_uuid: "..."                            # single resulting revision for the whole batch
}
```

Bulk transition must produce **one** resulting revision for the whole batch (not one revision per
step), so freezing a plan is a single append, not ~200.

## 6. Legal transition model

- `draft → ready_for_review` — author marks a step prepared; no cascade needed (still directly
  mutable up to this point).
- `ready_for_review → frozen` — publish/freeze; requires the scope's mechanical gate green when
  `require_green=true`. After this, the step is no longer directly mutable; further change requires
  cascade discipline (consistent with the existing `frozen` semantics).
- `ready_for_review → draft` and `frozen → draft` — allowed to reopen for editing; a `frozen → *`
  transition requires an open `cascade_uuid` (since frozen artifacts change only under cascade).
- Idempotent: transitioning a step already at `to_status` is a no-op reported under `skipped`, not an
  error.
- `needs_review`, `in_progress`, `done` are out of scope here — they are cascade-invalidation and
  execution-runtime states with their own transitions; this request covers only the authoring
  lifecycle `draft ↔ ready_for_review ↔ frozen`.

## 7. Acceptance criteria

1. `step_transition(plan, to_status="frozen", scope="whole_plan")` on a gate-green plan moves every
   `draft`/`ready_for_review` step under scope to `frozen` and returns them in `transitioned`.
2. Exactly **one** new revision is produced for a bulk transition, regardless of step count.
3. After a `whole_plan → frozen` transition, `plan_prompt_chain(role="coder")` returns a non-empty
   corpus: every AS appears once in `blocks.as` and in exactly one wave; `assembly` is non-empty.
4. `require_green=true` refuses to freeze a scope whose mechanical gate is red, with an explicit
   error and no partial transition.
5. Illegal transitions (e.g. `draft → frozen` skipping review, if the model forbids it, or
   `frozen → draft` without `cascade_uuid`) are rejected with an explicit, programmatically
   distinguishable error; legal ones succeed.
6. `dry_run=true` reports the exact `transitioned`/`skipped` sets and mutates nothing.
7. Idempotency: re-running the same transition reports all targets under `skipped` (already at
   status) and produces no spurious revision.
8. `step_get`/`step_tree`/`plan_status` report the new authoritative `status` after transition
   (single source of truth — not an inert `fields.status`).
9. Additive, non-breaking: existing commands (`step_update`, `plan_prompt_chain`, `plan_validate`,
   cascade family) keep their current contracts.

## 8. Non-goals

- Not proposing runtime/execution status transitions (`in_progress`, `done`) — those belong to the
  `runtime_*` command model.
- Not proposing automatic freeze as a side effect of scoring or `cascade_commit` — freeze must be an
  explicit, auditable operation (governance gate).
- Not changing `plan_prompt_chain`'s correct refusal to compile `draft` steps.

## 9. Open questions for the plan-manager team

- Does a transition path already exist that we missed (e.g. `branch_verify` or a scoring pass
  promoting `ready_for_review → frozen`)? If so, please document the exact command/flow — a new
  command is unnecessary if an existing one does this. `info` did not surface one.
- Should `draft → frozen` be allowed directly (single step), or must every step pass through
  `ready_for_review`? mwps is fine with either; we only need a bulk path to `frozen`.
- Is a green mechanical gate a precondition you want enforced inside `step_transition`, or should the
  caller be trusted to have validated first?

## 10. Related requests

- `docs/requests/planmgr_prompt_chain_command_request.md` — the consumer of frozen steps
  (`plan_prompt_chain`, implemented in 0.1.4). This request unblocks it: without a transition to
  `frozen`/`ready_for_review`, `plan_prompt_chain` can only ever return the fixed `tool_instructions`
  block for a freshly-authored plan.
- `docs/requests/planmgr_working_state_dump_request.md`, `…_context_block_commands_request.md` —
  prior requests in the same authoring/execution pipeline.
