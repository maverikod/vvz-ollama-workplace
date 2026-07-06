# Bug Report: `plan_prompt_chain` fails "parent of step A-NNN not found in nodes" at every scope

**Author:** Vasiliy Zdanovskiy
**email:** vasilyvz@gmail.com
**Date:** 2026-07-07
**Requesting project:** mwps (Agent Workstation)
**planmgr version:** 0.1.8 (build 2026-07-06T22:25:09Z)
**Severity:** blocker — `plan_prompt_chain` returns no corpus for a fully frozen, gate-green plan

## 1. Summary

After freezing an entire plan to `frozen` (all GS/TS/AS) on a green mechanical gate,
`plan_prompt_chain` fails with an internal error for **every** scope — `whole_plan`, a single
`G-NNN`, and a single `G-NNN/T-NNN`:

```
-32603 Command execution error: parent of step A-002 not found in nodes
        (original_error: "parent of step A-002 not found in nodes")
```

The step whose parent "is not found" is always an **atomic step** (`A-001` / `A-002`), and the
reported id is the **local** step id, not a full path. No corpus is returned.

## 2. Environment / plan state (all verified healthy)

- Plan: `workspace_orchestration_refactoring`, uuid `e271ef77-0e62-4450-8bfa-f253659a0534`.
- Head after freeze: `7a50ee42-3d07-4d9a-9c47-0cbf4ababebc`.
- `step_transition(scope="whole_plan", to_status="frozen")` succeeded: **all** GS/TS/AS moved to
  `frozen`, `skipped: []`, `gate.green: true`, `finding_count: 0`, one batch revision.
- `plan_validate` is green on every check including `coverage.*`.
- Tree is intact: the freeze response enumerated every AS with a correct full `path`
  (e.g. `G-006/T-001/A-001`) and a distinct `uuid`; `step_get("G-006/T-001/A-001")` returns
  `parent_path: "G-006/T-001"`, `parent_uuid: "0d9cb8d9-…"`, `status: "frozen"`.

So the plan data is well-formed; the failure is inside `plan_prompt_chain` assembly.

## 3. Reproduction

All three calls fail identically (queue-bound; error surfaced via `queue_get_job_status`):

1. `plan_prompt_chain(plan=…, revision="head", scope="whole_plan", role="coder")`
   → `-32603 … parent of step A-002 not found in nodes`
2. `plan_prompt_chain(plan=…, revision="head", scope="G-006", role="coder")`
   → `-32603 … parent of step A-001 not found in nodes`
3. `plan_prompt_chain(plan=…, revision="head", scope="G-006/T-001", role="coder")`
   → `-32603 … parent of step A-001 not found in nodes`

(Before the freeze, the same calls returned success with an **empty** corpus — expected, since
steps were `draft` and `include_statuses` defaults to `{frozen, ready_for_review}`. The error
appears only once there are eligible frozen steps to assemble, i.e. it is on the assembly path.)

## 4. Expected

A non-empty corpus: `blocks.as` populated, `assembly` non-empty, every AS in exactly one wave,
`tool_instructions.coder` present (it already is). For `role="coder"`, `assembly[i].use` should be
`{as, tool_instructions}` and each entry needs `branch_path`/`wave`, which requires resolving each
AS's parent chain.

## 5. Likely root cause

Step ids are **local to their parent**: `A-001`, `A-002`, `T-001`, etc. repeat across the tree
(there is a `G-001/T-002/A-001` and a `G-006/T-001/A-001`, both with local id `A-001`). The
assembly step appears to build its `nodes` lookup and resolve each atomic step's parent by a key
that is **not globally unique** — most likely the local `step_id` (or a partial key) rather than the
step `uuid` or full `path`. A parent lookup by local id then misses (or would collide), producing
"parent of step A-002 not found in nodes".

Every step already carries a unique `uuid` and a unique full `path`, and `step_get` exposes
`parent_uuid` and `parent_path`. Resolving the parent by `parent_uuid` (or full `path`) instead of
by local `step_id` should fix it.

## 6. Acceptance for the fix

1. `plan_prompt_chain(scope="whole_plan", role="coder")` on plan `e271ef77-…` at head
   `7a50ee42-…` returns success with `counts.as == number of AS in the plan`, `assembly` of the
   same length, and non-empty `waves` covering every AS exactly once.
2. Scoped calls `scope="G-006"` and `scope="G-006/T-001"` succeed and return only the AS under that
   scope, each with a correct `branch_path` reflecting its true parent chain.
3. Parent resolution is by `uuid`/full `path`, so duplicated local `step_id`s across the tree no
   longer collide or miss.
4. `role="review"`/`role="conscience"` assemble the same tree without the error (upper-layer
   selectors resolve their parents too).

## 7. Notes

- This blocks the execution pipeline end-to-end: freeze now works (0.1.8 `step_transition`), so the
  only remaining gap between a committed green plan and an executable coder corpus is this parent
  resolution.
- Related: `docs/requests/planmgr_prompt_chain_command_request.md` (the command spec),
  `docs/requests/planmgr_step_status_transition_request.md` (the freeze command, delivered in 0.1.8).
