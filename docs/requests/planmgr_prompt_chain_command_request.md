# Feature Request: `plan_prompt_chain` command for plan-manager

**Author:** Vasiliy Zdanovskiy
**email:** vasilyvz@gmail.com
**Date:** 2026-07-05
**Requesting project:** mwps (Agent Workstation)
**Requesting plan:** `docs/plans/workspace_orchestration_refactoring/`

## Table of contents

1. Motivation
2. Current state in planmgr
3. Proposed command: `plan_prompt_chain`
4. Output structure
5. Ordering keys
6. Boundary of responsibility
7. Consumer-side contract (context only, out of scope)
8. Acceptance criteria
9. Non-goals
10. Open questions for plan-manager team
11. References
12. Appendix A — cited binding paragraphs (verbatim)

## 1. Motivation

mwps executes green (mechanically gated) plans as chains of prompts sent to small executor
models. Per mwps HRS (`source_spec.md`, "Plan-driven prompt chains" and "Model roles and
tiering"), every atomic-step prompt is composed of five layers, most to least stable: HRS
fragment(s), MRS fragment(s), global step (GS), tactical step (TS), atomic step (A-step).

Two A-prompts under the same TS differ only in their tail — the A-step layer and sometimes the
target-file excerpt. Everything above (standards, HRS, MRS, GS, TS) is byte-identical across
all atomic steps of the same branch. This is a strictly hierarchical common-prefix structure:
TS-siblings share a TS prefix, GS-siblings share a shorter GS prefix, the whole plan shares a
plan-level prefix. Provider prompt caching ({s2b5}, {z1u7}, {t9c3}) rewards exactly this shape.

Running plans as prompt chains is therefore the mechanism that makes execution on small, cheap
models affordable at all ({e4a1}: final executors are Haiku/GPT-nano-class or a local
qwen-class model with VRAM-bounded, non-fixed capacity).

planmgr today exposes `branch_prompt` (one step/branch at a time) and `graph_order` /
`graph_parallel_map` (order and dependency waves), but no command returns the **entire** chain
for a plan or sub-branch in one structured, deduplicated response with both ordering
strategies attached. Consumers must currently call `branch_prompt` once per atomic step and
re-derive prefix sharing and ordering themselves — work plan-manager, as the plan-tree owner,
is better placed to do once.

## 2. Current state in planmgr

As understood by the requester (mwps side); plan-manager team to confirm:

- `branch_prompt` — one prompt per call; no batching, no block-level structure, no dedup.
- `graph_order` — linear, dependency-respecting execution order over the plan graph.
- `graph_parallel_map` — dependency waves for parallel execution.
- `plan_validate` / gate scoring (`plan_score` or equivalent) — checks invariants I1–I3, reports
  gate color.

None of these, alone or combined, produce a single deduplicated, chain-wide, dual-order
artifact. `plan_prompt_chain` fills that gap as a new, additive command.

## 3. Proposed command: `plan_prompt_chain`

### Parameters

| Name | Required | Default | Description |
|---|---|---|---|
| `plan` | yes | — | Plan name (`docs/plans/<plan_name>/`). |
| `revision` | no | head | Pins the chain to a specific plan revision, for reproducibility. Unknown revision is an error (§8). |
| `scope` | no | whole plan | A sub-branch: `G-NNN` or `G-NNN/T-NNN`. |
| `include_statuses` | no | `[frozen, ready_for_review]`* | Eligible `status` values per `plan_standard_machine.yaml` → `statuses`. *Exact default to confirm — see §10. |

### Precondition

The mechanical gate for `scope` must be green before assembly — the same check `plan_score` (or
equivalent) performs. If red, the command fails with `GATE_RED` and returns no partial chain,
consistent with {b3x2}: "After a plan reaches a green mechanical gate in plan-manager, a prompt
chain is assembled from it."

## 4. Output structure

The command returns **structured data**, not a text blob or a list of ready prompt strings.
Tokenization, padding, and provider-specific formatting are consumer responsibilities (§6); a
text-only output would either bake consumer formatting into plan-manager or force the consumer
to re-parse text back into blocks.

```
{
  "plan": "<plan_name>", "revision": "<resolved_revision_id>",
  "scope": "<whole_plan | G-NNN | G-NNN/T-NNN>",
  "blocks": {
    "<block_id>": {
      "block_id": "<stable_id>",
      "type": "hrs_fragment | mrs_fragment | global_step | tactical_step | atomic_step",
      "source_ref": ["<source_spec label(s) / concept_id(s) / step_id>"],
      "content": "<canonical block content, no provider-specific formatting>"
    }
  },
  "steps": [
    {
      "step_id": "A-NNN", "target_file": "<path>",
      "operation": "create_file | modify_file | delete_file | rename_file",
      "priority": <int>, "block_ids": ["<block_id>", "..."],
      "wave": <int>, "branch_path": "G-NNN/T-NNN", "depends_on": ["A-NNN", "..."]
    }
  ]
}
```

`blocks`: one entry per distinct HRS/MRS fragment, GS, TS, A-step in the chain for `scope`.
**Shared blocks are emitted exactly once** and referenced by `block_id` from every step that
uses them (e.g. a block shared by 40 atomic steps under one TS appears once, not 40 times) —
this dedup is the basis for prefix-cache planning downstream. `source_ref` traces the block to
its origin (`source_spec` label, `concept_id`, or owning `step_id`). `content` is canonically
serialized (stable, see §8) but carries no tokenizer alignment, padding, injected standards, or
provider wrapper.

`steps`: one entry per atomic step in `scope`, carrying the same dependency information
`graph_order`/`graph_parallel_map` already expose (`depends_on`), so this command supersedes
calling those separately for chain-execution purposes without changing their existing
contracts for other callers. `block_ids` lists blocks in composition order (HRS → MRS → GS → TS
→ A-step). `priority`/`target_file` mirror the atomic step's own fields per
`plan_standard_machine.yaml` (`atomic_step.required_fields`); the one-file-per-step and
distinct-priority-per-file rules apply unchanged and are not re-validated here (that is
`plan_validate`'s job).

## 5. Ordering keys

Per {d9z4}, two orderings are supported and the strategy choice belongs to the consumer, not
plan-manager. Every step therefore carries **both** keys, unconditionally:

- **`wave`** (integer) — dependency-wave index, equivalent to `graph_parallel_map`'s grouping.
  Steps sharing a `wave` have no dependency relation within `scope` and may run in parallel.
  Maximizes parallelism.
- **`branch_path` + `priority`** — a depth-first key (`G-NNN` then `T-NNN` then `priority`
  within the TS's atomic-step set). Sorting by this key groups steps sharing the deepest common
  prefix adjacently, maximizing cache-prefix reuse under sequential execution.

`plan_prompt_chain` does not pick a strategy or pre-sort `steps` into one privileged order —
callers sort/group by whichever key they need.

## 6. Boundary of responsibility

`plan_prompt_chain` must **not** perform, and the output must contain no trace of: tokenization
or token counting; padding/alignment to any token boundary (the 256-token alignment mwps
applies, {c5y8}, is entirely consumer-side); injection of standards at the head of the prefix;
provider-specific cache-breakpoint markers or message-role wrapping; model-tier selection or
executor-capacity checks (owned by mwps via model-access-core, {e4a1}).

This is a hard boundary: mwps's `context_manager` is the single owner of tokenizer-aware and
provider-facing formatting across the whole context pipeline — dialogue slots and plan chains
alike ({s9b4}, {m1w4}). Duplicating any of it into plan-manager would create two divergent
sources of truth for how a prompt is finally rendered. plan-manager's contract ends at
"structured, deduplicated, canonically-serialized blocks plus both ordering keys."

## 7. Consumer-side contract (context only, out of scope for this request)

Shown so the plan-manager team can see why §6's boundary is drawn where it is — none of this is
requested of plan-manager. mwps's `context_manager` consumes the chain output and, per {c5y8}
and {e4a1}: prepends role-appropriate standards at the head of the shared prefix; serializes
blocks canonically and pads them to 256-token boundaries (tokenizer-aware; this rule applies to
plan chains only, never dialogue slots); places provider cache breakpoints on block boundaries;
validates each atomic prompt (standards + blocks + padding + harness + reserved output budget)
against the executor's *measured* capacity via `model_estimate_request_capacity`; on overflow
escalates to a larger executor tier, or — if no tier fits — surfaces a plan defect requiring
tactical-level revision; logs every execution in the dialogue journal with plan/step
identifiers ({f7b6}), closing the trace HRS paragraph → concept → step → prompt → execution →
Conscience verdict.

## 8. Acceptance criteria

1. **Determinism.** Same `plan` + resolved `revision` → byte-identical `blocks` content and an
   identical `steps` array (values and order) on repeated calls. No timestamps, random ids, or
   non-canonical ordering in block/step content or ids.
2. **Block deduplication.** No two blocks with identical `source_ref`+`content` get distinct
   `block_id`s; every step sharing that content references the same `block_id`.
3. **Full coverage.** Every atomic step in `scope` whose ancestor chain and own status fall
   within `include_statuses` appears exactly once in `steps`; none silently dropped.
4. **Both ordering keys present.** Every step has non-null `wave` and non-null
   `branch_path`+`priority`; `wave` values agree with `graph_parallel_map` for the same
   scope/revision; `branch_path`+`priority` sorting reproduces a valid depth-first traversal
   restricted to `scope`.
5. **Gate enforcement.** Red gate for `scope` → explicit `GATE_RED` error, no partial payload.
6. **Revision validation.** Unknown `revision` → explicit "unknown revision" error, never a
   silent fallback to head.
7. **Standard compatibility.** `atomic_step` blocks, together with their ancestor blocks in the
   same step's `block_ids`, are sufficient to reconstruct everything
   `atomic_step.context_budget.full_context_includes` (`plan_standard_machine.yaml`) lists, with
   no additional plan-manager call needed.
8. **No consumer-side concerns leak in.** No block content contains token-boundary padding,
   injected standards text, or provider-specific markup (spot-checked; §6).
9. **Scope restriction is exact.** `scope = G-NNN/T-NNN` returns only blocks/steps reachable
   from that TS (its atomic steps, its own TS block, parent GS block, referenced HRS/MRS
   fragments) — no sibling TS content.
10. **Additive, non-breaking.** Introducing this command does not change the existing output
    contracts of `branch_prompt`, `graph_order`, `graph_parallel_map`, or `plan_validate`/gate
    scoring.

## 9. Non-goals

- Does not replace `branch_prompt` for single-step or human-inspection use — both coexist.
- Does not decide which ordering (§5) to execute with, or dispatch any prompt — consumer's call.
- Does not perform tokenization, padding, capacity validation, or standards injection (§6) —
  explicitly out of scope, not merely deferred.
- Does not decide model tier or executor assignment — owned by model-access-core sessions per
  {g5c2}/{h2d8}, consumed by mwps, not by plan-manager.

## 10. Open questions for plan-manager team

- Exact default `include_statuses`: `[frozen]` only, or `[frozen, ready_for_review]`? Should any
  `needs_review`/`in_progress` step within scope hard-fail rather than be silently excluded?
- Error taxonomy: distinct error types for `GATE_RED` vs. "unknown revision", or variants of one
  generic validation error? mwps only needs them programmatically distinguishable.
- Does `revision` address a git-level revision of the plan directory, an internal plan-manager
  revision counter, or should both be accepted as aliases?

## 11. References

- mwps HRS: `docs/plans/workspace_orchestration_refactoring/source_spec.md` — "Plan-driven
  prompt chains" ({b3x2}, {c5y8}, {d9z4}, {e4a1}, {f7b6}); "Model roles and tiering" ({g5c2},
  {h2d8}).
- `docs/standards/plan_standard_machine.yaml` — artifact levels 3–5 (`global_step`,
  `tactical_step`, `atomic_step`), `atomic_step.context_budget`, `atomic_step.one_file_rule`,
  `statuses`.
- Existing plan-manager commands referenced (as currently understood; plan-manager team to
  confirm exact signatures): `branch_prompt`, `graph_order`, `graph_parallel_map`,
  `plan_validate` / gate scoring.

## Appendix A — cited binding paragraphs (verbatim)

From `docs/plans/workspace_orchestration_refactoring/source_spec.md`:

> {b3x2} After a plan reaches a green mechanical gate in plan-manager, a prompt chain is
> assembled from it: for every atomic step, in execution order, a structured set of typed
> blocks — HRS fragment, MRS fragment, global step, tactical step, atomic step — with blocks
> shared between steps emitted once and referenced. Chain assembly is a new plan-manager
> command; it is an external dependency implemented in the plan-manager project and consumed
> by mwps.

> {c5y8} mwps (the context_manager) wraps the raw chain into executable prompts:
> role-appropriate standards are prepended at the very start of the shared prefix; blocks are
> serialized canonically and aligned to 256-token boundaries using tokenizer-aware padding;
> provider cache breakpoints are placed on block boundaries. The 256-token alignment applies to
> plan prompt chains only, not to dialogue context slots.

> {d9z4} Chain prompts share hierarchical prefixes (standards → HRS/MRS fragments and global
> step → tactical step → atomic step). Two execution orderings are supported: depth-first over
> the plan tree, which maximizes cache prefix reuse, and dependency waves from the plan graph,
> which maximizes parallelism. The strategy is chosen per run.

> {e4a1} The final executors of chain prompts — the code-writing models — are small models:
> Haiku / GPT-nano class or a local qwen-class model. Its effective context capacity is not a
> fixed constant: it is determined by the VRAM remaining after model weights are loaded, via the
> calibrated per-token KV-cache cost measured by model-access-core hardware calibration. Every
> assembled atomic prompt — standards, padding, and harness included — together with the
> reserved output tokens for the generated code is validated against that measured capacity
> through `model_estimate_request_capacity` at chain assembly time; an overflow routes the step
> to a larger executor tier, and only if no tier fits is it a plan defect requiring
> tactical-level revision.

> {f7b6} Every chain prompt execution is logged in the dialogue journal with its plan and step
> identifiers, closing the end-to-end trace from HRS paragraph to concept, step, prompt,
> execution, and Conscience verdict.

> {g5c2} Plan authoring uses tiered models matched to the abstraction level of the artifact. HRS
> work, MRS projection, and concept extraction are performed by top-tier models (Opus / Fable /
> GPT-5.5 class). Global steps and tactical steps are authored by mid-tier models (Sonnet /
> GPT-mini class). Atomic steps are authored by small models (Haiku / GPT-nano class, optionally
> a local qwen-class model). The tier-to-model mapping is configuration resolved through
> model-access-core sessions, never hardcoded.

> {h2d8} Cheaper authoring at lower levels is structurally guarded: lower-level authors work
> only from frozen upper artifacts, the coverage matrices, and the standards, and their output
> must pass the mechanical gate and the level's consistency checks. A gate or consistency
> failure escalates the artifact to the next model tier up; only after the top tier fails is the
> defect surfaced to the human.
