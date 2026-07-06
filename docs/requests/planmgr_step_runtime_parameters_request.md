# Feature Request: step runtime parameters for plan-manager

**Author:** Vasiliy Zdanovskiy
**email:** vasilyvz@gmail.com
**Date:** 2026-07-06
**Requesting project:** mwps (plan `workspace_orchestration_refactoring`)

## Table of contents

1. Motivation
2. Current state in planmgr (as understood by the requester)
3. Data model
4. Proposed commands
5. Interaction with existing mechanisms
6. Concurrency model
7. Export/import boundary
8. Acceptance criteria
9. Non-goals
10. Open questions for plan-manager team
11. References
12. Appendix A — cited binding paragraphs (verbatim)

## 1. Motivation

mwps chats branch freely: a single chat may carry work on several plan steps over its lifetime,
and any one message may relate to zero, one, or several steps at once. Per mwps HRS ("Task
threads"), a chat has at most one **current task** — a plan step explicitly activated by the
user or the orchestrator ({x6j3}) — and every journal record carries at most one **direct**
task link to that current task, marking the message as work on it ({y8k5}). Beyond that
deterministic link, a record may carry any number of **indirect** links, mediated by shared MRS
concepts the context builder tags the message with; these are advisory retrieval hints, never
gate or status inputs ({z4m2}).

This direct/indirect linkage is computed and owned by mwps (the dialogue journal is the source
of truth for it), but plan-manager is the owner of the plan step itself, and the ecosystem
principle mwps follows throughout is that a service exposes state about its own entities through
its own API rather than have consumers reconstruct it externally. HRS paragraph {c3q7} is
explicit that plan-manager must reflect this linkage: "Plan-manager reflects this linkage as
runtime parameters of plan steps, kept distinct from the cascade-governed definition fields."

The critical constraint is that this reflection must not touch the plan **definition**.
plan-manager already treats step definition as cascade-governed, append-only-revisioned,
mechanically gated content ({c3q7}: "Runtime parameters never mutate the plan definition and
never trigger the cascade"). Task-thread linkage, execution history, and authoring provenance
are facts *about* a step's life in the surrounding system, not facts that redefine the step
itself — they must be writable at arbitrary frequency (once per chat message, potentially),
against a step of any status including `frozen`, without perturbing plan revisions, gate
verdicts, or semantic scores. This request asks plan-manager to add exactly that: a new,
cascade-free runtime layer, orthogonal to the existing definition layer.

## 2. Current state in planmgr (as understood by the requester)

- Plans live in a versionable store with head revisions; every mutation of definition fields
  produces a new append-only revision.
- Definition mutations affecting MRS concepts run only inside a cascade transaction
  (`cascade_begin`/`cascade_commit`), holding a per-plan lock for the duration.
- Steps carry a `status` — `draft`, `ready_for_review`, `frozen`, `needs_review` — governed by
  the mechanical gate plus semantic scoring.
- Plan definitions round-trip through a file-based export/import format
  (`plan_export`/`plan_import`, `hrs_export`/`hrs_import`).
- Nothing in the current command surface stores information *about* a step's execution or
  discussion history; today that information exists only in mwps's own dialogue journal, keyed
  by `plan` + `step_id`, with plan-manager unaware of it.

plan-manager team to confirm/correct any of the above.

## 3. Data model

Runtime parameters are a per-step record, addressed by `(plan, step_id)`, held in a store
distinct from the definition tables — no shared rows, no shared revision counter. Minimum
fields, extensible without a breaking change:

- **`activations`** — append-only list of task-thread episodes: `{activation_id, chat_id,
  started_at, ended_at?}`. One entry per episode where this step was *the* current task of
  `chat_id` ({x6j3}); `ended_at` is null while the task is still current in that chat.
- **`execution_attempts`** — append-only list of chain-prompt execution attempts: `{attempt_id,
  session_id, executor: {model_type, provider}, result: success | gate_red | escalated | error,
  usage: {tokens_in, tokens_out, cost}, started_at, ended_at}`. `executor.model_type` /
  `executor.provider` follow the same two-field shape as the dialogue journal's model-author
  fields, per {j8e4} and the journal schema it aligns with — one shape for "which model did
  this" across mwps and plan-manager.
- **`journal_aggregates`** — a single object, not a list: `{direct_count, indirect_count,
  total_cost, last_linked_at}`. This is *pushed* by mwps as a computed summary over the journal
  records linked to this step (direct and indirect, per {y8k5}/{z4m2}); plan-manager never
  queries Redis or the mwps journal itself to compute it — plan-manager is a passive recipient
  here, mwps remains the source of truth for linkage.
- **`authoring`** — `{model_type, provider, authored_at}`: which model composed the step's
  artifact, per {j8e4}. This belongs in the runtime layer specifically *because* a frozen step's
  definition is immutable — recording "who authored this" as a definition field would require a
  new revision (and possibly re-gating) every time provenance is attached or corrected, which
  defeats the point of freezing. The runtime layer lets authoring be recorded, and later
  corrected, without touching the frozen artifact at all.

## 4. Proposed commands

```
step_runtime_get(plan, step_id) -> RuntimeRecord

step_runtime_report(plan, step_id, payload) -> RuntimeRecord
  # payload: partial RuntimeRecord — any subset of activations / execution_attempts /
  # journal_aggregates / authoring.

step_runtime_list(plan, scope?) -> { "<step_id>": RuntimeRecord, ... }
  # scope: optional G-NNN or G-NNN/T-NNN restriction, default whole plan.
```

Optionally, `include_runtime: bool = false` on the existing `step_get`/`step_tree` commands,
returning each step's `RuntimeRecord` inline for callers (e.g. a dashboard) that want definition
and runtime together in one call without a second round trip.

**Merge semantics of `step_runtime_report`:**

- `activations` and `execution_attempts` are **append** targets: each entry carries a
  client-generated id (`activation_id` / `attempt_id`) minted by mwps. A `step_runtime_report`
  call resubmitting an id already present is a no-op on that entry (idempotent retry), not a
  duplicate append — mwps may retry a report after a timeout without risk of double-counting.
- `journal_aggregates` is a **replace-if-newer** target: plan-manager accepts a submitted object
  only if its `last_linked_at` is not older than the currently stored one, otherwise the call is
  a no-op for that field (protects against an out-of-order retry clobbering a newer aggregate
  with a stale one). `direct_count`/`indirect_count`/`total_cost` are always the full current
  values as computed by mwps, not deltas — plan-manager does no arithmetic on them.
- `authoring` is a **replace** target: the latest reported value wins; mwps is expected to call
  this once per artifact composition (or recomposition), not per message.
- A single `step_runtime_report` call may set any subset of these four fields in one payload.

## 5. Interaction with existing mechanisms

Per-mechanism statement, each normative:

- **Revisions.** `step_runtime_report` never creates a new plan revision. The head revision
  before and after the call is identical.
- **Cascade.** `step_runtime_report` never requires, opens, or participates in a
  `cascade_begin`/`cascade_commit` transaction, and never contends for the per-plan cascade lock.
- **Step status.** Runtime parameters can be written for a step in any status — `draft`,
  `ready_for_review`, `frozen`, `needs_review` — without changing that status, and writing them
  never itself causes a status transition.
- **Mechanical gate.** Gate evaluation for a plan or scope is computed from definition fields
  only; runtime-parameter content is not read by the gate and cannot change its verdict.
- **Semantic scoring.** Scoring likewise ignores runtime parameters entirely; two plans
  identical in definition but differing in runtime-parameter content score identically.
- **Export/import.** See §7.

## 6. Concurrency model

No plan-wide lock. The cascade's per-plan lock exists to serialize MRS-affecting definition
mutations, which are comparatively rare; task-thread activity is comparatively frequent (up to
once per chat message) and must not queue behind, or block, cascade transactions on the same
plan, nor vice versa. Per-step atomicity is sufficient: two concurrent `step_runtime_report`
calls against the *same* step must not lose an append (§4's idempotent-append and
replace-if-newer rules assume this), but calls against different steps of the same plan, or a
`step_runtime_report` and a concurrent `cascade_begin`/`cascade_commit` on the same plan, must
proceed independently.

## 7. Export/import boundary

Runtime parameters are **not** part of the default `plan_export`/`plan_import` (or
`hrs_export`/`hrs_import`) payload — the exchange format continues to describe definition only,
keeping it portable and diffable independent of any one deployment's runtime history. A separate,
optional sidecar export (e.g. `step_runtime_export(plan, scope?)`) may be added for analytics
consumers that want runtime data alongside a definition snapshot; it is additive and out of
scope for the round-trip contract `plan_import` must preserve.

## 8. Acceptance criteria

1. **No new revision.** The plan's head revision id is identical immediately before and after a
   `step_runtime_report` call.
2. **No cascade.** `step_runtime_report` succeeds with no open `cascade_begin` transaction, and
   does not implicitly open or require one.
3. **Any status writable.** `step_runtime_report` succeeds against a step whose status is
   `frozen` (and every other status), and the step's status is unchanged by the call.
4. **Idempotent append.** Resubmitting `step_runtime_report` with an `activation_id` or
   `attempt_id` already recorded produces no duplicate entry in `step_runtime_get`'s output.
5. **Gate/score blindness.** Two plans identical in every definition field but differing in
   runtime-parameter content produce byte-identical mechanical gate verdicts and semantic scores
   for the same scope.
6. **Export purity.** Default `plan_export`/`hrs_export` output contains no runtime-parameter
   data; only an explicit sidecar export command includes it.
7. **Read completeness.** `step_runtime_get` returns all four field groups (`activations`,
   `execution_attempts`, `journal_aggregates`, `authoring`) as specified; `step_runtime_list`
   over the whole plan returns an entry for every step, including steps with no runtime data yet
   (empty record, not an omission).
8. **No plan-wide lock.** A `step_runtime_report` on step B does not block, or get blocked by, a
   concurrent `cascade_begin`/`cascade_commit` transaction on the same plan affecting step A.
9. **No auto status transition.** Reporting a `journal_aggregates` payload with arbitrarily high
   `indirect_count`/`total_cost` never changes the step's `status`, gate color, or score, in any
   combination.
10. **Passive aggregate recipient.** plan-manager performs no read against Redis or any
    mwps-owned store to populate or validate `journal_aggregates`; the value stored is exactly
    the value last accepted via `step_runtime_report` (subject to rule 4 of §4).

## 9. Non-goals

- Not an analytics database. plan-manager stores the aggregate counters mwps pushes; it does not
  compute, re-derive, or independently validate them, and does not offer ad hoc querying beyond
  `step_runtime_get`/`step_runtime_list`.
- Not a replacement for the mwps dialogue journal. The journal in Redis remains the source of
  truth for direct/indirect linkage, per-message detail, and full execution logs ({y8k5},
  {z4m2}, {f7b6}); plan-manager holds only the aggregates and attempt summaries mwps chooses to
  push, not the underlying messages.
- Not a gate or scoring input, ever (§5, §8.9) — this is deliberately excluded, not merely
  deferred: discussion-density signals inform a human that a step may be under-specified and a
  candidate for `needs_review`, but no automatic transition may be built on top of runtime
  parameters, in this request or in any future extension of it.
- Not part of the plan-manager `plan_export`/`plan_import` round-trip contract (§7).

## 10. Open questions for plan-manager team

- Should `step_runtime_list` support pagination for very large plans, or is one response per
  plan/scope acceptable given the expected record sizes?
- Is `replace-if-newer` on `journal_aggregates` (§4) an acceptable semantic, or does plan-manager
  prefer a monotonic-only merge (reject any `last_linked_at` not strictly greater, rather than
  "not older")?
- Should `execution_attempts` and `activations` have a retention/trim policy (e.g. cap per step,
  archive older entries), or is unbounded append acceptable for the expected plan lifetimes?
- Does plan-manager want a distinct error type for "unknown step_id" vs. "unknown plan" on
  `step_runtime_get`/`step_runtime_report`, mirroring the error taxonomy question raised for
  `plan_prompt_chain` (see References)?

## 11. References

- mwps HRS: `docs/plans/workspace_orchestration_refactoring/source_spec.md` — "Task threads"
  ({x6j3}, {y8k5}, {z4m2}, {a2n9}, {b9p4}, {c3q7}); "Model roles and tiering" ({j8e4});
  "Plan-driven prompt chains" ({f7b6}).
- Related, independent requests to the plan-manager team:
  `docs/requests/planmgr_prompt_chain_command_request.md` (`plan_prompt_chain` command) and
  `docs/requests/planmgr_file_exchange_interface_request.md` (file-exchange path for import
  commands). This is the third request in the series; all three are additive and independent of
  one another.

## Appendix A — cited binding paragraphs (verbatim)

From `docs/plans/workspace_orchestration_refactoring/source_spec.md`:

> {x6j3} A chat has at most one current task — a plan step (plan plus `step_id` from
> plan-manager) explicitly activated by the user or the orchestrator. The current task is
> per-chat state and an anchor of the same kind as the current project: activation is explicit,
> never inferred from message topics.

> {y8k5} A journal record has at most one direct task link — to the current task that was active
> when the message was processed, or to the chain step that produced it. The direct link is
> deterministic and normative: it marks the message as work on that task.

> {z4m2} A record may additionally carry any number of indirect task links, mediated by shared
> MRS concepts: the context builder tags each message with the concept ids it touches, and the
> plan steps covering those concepts receive indirect links, with the mediating concepts
> recorded. Indirect links are advisory retrieval hints; they are never inputs to gates or
> statuses.

> {c3q7} Plan-manager reflects this linkage as runtime parameters of plan steps, kept distinct
> from the cascade-governed definition fields: at minimum, activation as a current task,
> execution attempts of chain prompts, and aggregates over directly and indirectly linked
> journal records (counts and cost). Runtime parameters never mutate the plan definition and
> never trigger the cascade; exposing them is an external dependency implemented in the
> plan-manager project.

> {j8e4} Every plan artifact records which model authored it — model type and provider as
> separate fields, consistent with the dialogue journal schema — so plan quality can be traced
> back to the authoring tier.

> {f7b6} Every chain prompt execution is logged in the dialogue journal with its plan and step
> identifiers, closing the end-to-end trace from HRS paragraph to concept, step, prompt,
> execution, and Conscience verdict.
