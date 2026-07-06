# Implementation Spec: context-block commands (compile per-step authoring context from concepts, as DB records)

**Author:** Vasiliy Zdanovskiy
**email:** <vasilyvz@gmail.com>
**Date:** 2026-07-06
**Requesting project:** mwps
**Target project:** plan-manager
**Status:** Ready for implementation
**Severity:** capability gap (tiered plan authoring assembles context out-of-band, by hand, not in the DB)

## Table of contents

1. Goal
2. Background and motivation
3. Design principles
4. Data model
5. Compilation algorithm
6. Commands
7. Determinism and hashing
8. Storage, versioning, lifecycle
9. Error taxonomy
10. Worked example (G-002 → tacticals)
11. Round-trip with prompt chains
12. Acceptance criteria (as tests)
13. Non-goals
14. Compatibility
15. Open decisions for the implementer
16. Related requests

---

## 1. Goal

Add read-only, cascade-aware commands to plan-manager that **compile the authoring context for any
plan node from a set of MRS concept ids** and store it as **typed block records in the database**
(not files). The compiled context is split, per parent step, into a **common** block (shared by all
its children, written first) and, per child, a **specific** block (the delta over common, written
after). An authoring model supplies only concept ids; plan-manager compiles, deduplicates, versions,
and enforces a downward-narrowing scope invariant.

The result: tiered plan authoring (top-tier model for HRS/MRS + global steps, mid-tier for tactical,
small-tier for atomic) reads each step's minimal, exact context directly from the plan instead of
having it hand-assembled and staged as files.

## 2. Background and motivation

plan-manager already stores, per plan, the fully-formalized upper artifacts:

- **HRS**: binding paragraphs, each `{ label (4-char), text, position, binding }`.
- **MRS concepts**: `{ concept_id (C-NNN), name, definition, properties[], source_labels[] }` where
  each `source_labels` entry is an HRS label such as `{a1k2}`.
- **MRS relations**: `{ from_concept, to_concept, type }`, `type ∈ {uses, owns, implements, extends,
  depends_on, produces, consumes}`.
- **Steps**: levels 3 (global, `G-NNN`), 4 (tactical, `T-NNN`), 5 (atomic, `A-NNN`); each binds a
  set of `concepts` (C-NNN) and holds level-specific fields; identified by a canonical path
  (`G-002/T-001/A-003`).
- A revision/cascade model over all of the above.

Because concepts carry `source_labels` and relations name their endpoint concepts, **a set of
concept ids fully and deterministically determines** the HRS fragments, the in-scope relations, and
the concept definitions that make up a step's context. Today an orchestrator re-derives this by hand,
copies the shared part into every child, and stages the result as scratch files disconnected from the
plan revision. This spec moves that derivation into plan-manager as deterministic, versioned,
deduplicated commands.

## 3. Design principles

1. **Concept is the join key; the model selects, the tool compiles.** The only authoring input is a
   set of concept ids. plan-manager compiles them into typed blocks. The model decides *which*
   concepts (the split), plan-manager decides *what content* they expand to.
2. **Two-phase per step: common first, then specific-as-delta.** For a parent, `context_common` is
   compiled and stored first; each child's `context_specific` is then compiled as a strict
   set-difference over the referenced common block, so a child never repeats common material.
3. **Recursive and narrowing.** Each node works only from the scope it inherited (its own bound
   concepts). It selects the subset common to all its children and the subset specific to each child;
   each child repeats the process. Scope strictly narrows downward: a child's concepts ⊆ the parent's
   scope. plan-manager enforces the narrowing; the model owns the selection.
4. **Records, not files.** Blocks are DB records returned inline over JSON-RPC. `export_root` is
   never involved.
5. **Deterministic and deduplicated.** Identical inputs at the same revision yield byte-identical
   blocks (same content hash). A common block is stored once and referenced by every child.
6. **Read-only over plan truth.** Compilation never mutates HRS/MRS/steps and never advances the head
   revision.
7. **Invariant per-step-type prose is baked into the tool, not written by the model.** Everything in
   an authoring prompt that is constant for a step *type* — the author-role instructions, the
   definition-of-done / no-placeholder standards, the field schema, and the output contract — depends
   only on `child_level` (G/T/A) and tier (top/mid/small), never on the plan. plan-manager holds
   these as versioned **per-level templates** and emits them as part of the common block. As a
   result the entire context prose is encoded — templates (baked) plus concept-derived content
   (from the DB) — and the authoring model writes no prose to obtain its context: it supplies concept
   ids and receives a ready-to-send prompt. The model's only free generation is its actual output
   (the step it authors).

## 4. Data model

### 4.1 ContextBlock record

| field | type | notes |
|---|---|---|
| `block_id` | string (uuid) | immutable identity of the stored block |
| `plan_uuid` | string | owning plan |
| `revision_uuid` | string | the plan revision the block was compiled against (head or cascade tip) |
| `cascade_uuid` | string \| null | set when compiled against an open cascade's working state |
| `node_path` | string | the parent step path the block is scoped to (`"plan"` for the top) |
| `child_level` | int (3\|4\|5) | the level of the children this context is for |
| `kind` | enum `common` \| `specific` | |
| `common_block_id` | string \| null | for `specific`: the common block it is a delta over |
| `scope_concepts` | string[] | for `common`: the node's inherited scope; for `specific`: the child's concept set |
| `content` | ContentBlock[] | ordered typed sub-blocks (§4.2) |
| `content_hash` | string (sha256 hex) | canonical hash of `content` (§7) |
| `created_at` | string (ISO-8601) | metadata only; **not** part of `content_hash` |

`block_id` is stable per `(plan_uuid, revision_uuid|cascade_uuid, node_path, kind, content_hash)`:
recompiling identical inputs returns the existing record (idempotent), it is not duplicated.

### 4.2 ContentBlock (typed sub-block)

`content` is an ordered list of typed sub-blocks. Each has a `type` and a type-specific payload:

- `authoring_template` — `{ type, level, tier, role_instructions, output_contract, template_version }`
  — the **baked, plan-independent** prose for authoring a step of this type: the author-role
  instructions ("you are the tactical author…"), the how-to-decompose guidance, and the exact output
  contract (the JSON shape to return). Depends only on `child_level` and `tier`; held as a versioned
  template in plan-manager, not written by any model.
- `standards` — `{ type, tier: "top"|"mid"|"small", text }` — role/level-appropriate standards
  (definition-of-done, coding standards). Source is configuration/doc-store; see §15.
- `field_schema` — `{ type, level, schema }` — the exact required-field skeleton for authoring a step
  at `child_level` (the level's declarative schema).
- `step_definition` — `{ type, path, name, description, fields }` — the parent node's own frozen
  definition (the upper artifact the children must conform to). Absent when `node_path == "plan"`.
- `hrs_fragment` — `{ type, label, text, position }` — one HRS binding paragraph.
- `mrs_concept` — `{ type, concept_id, name, definition, properties[] }` — one concept.
- `mrs_relation` — `{ type, from_concept, to_concept, relation_type }` — one relation.

Only `hrs_fragment`, `mrs_concept`, `mrs_relation` participate in the common/specific delta;
`authoring_template`, `standards`, `field_schema`, `step_definition` appear only in the `common`
block. Together `authoring_template` + `standards` + `field_schema` are the fully-baked, plan-
independent prose — the model never authors them.

## 5. Compilation algorithm

### 5.1 Primitive: compile a concept set

`compile(plan, rev, S)` where `S` is a set of concept ids returns three lists derived purely from the
plan at revision `rev`:

1. **concepts**: for each `c ∈ S` (dedup), an `mrs_concept` sub-block from the stored concept.
2. **hrs_fragments**: `L = ⋃ source_labels(c) for c ∈ S`; for each label in `L`, the stored HRS
   binding paragraph as an `hrs_fragment`. Deduplicated by label.
3. **relations**: every stored relation whose `from_concept ∈ S`, as an `mrs_relation`. `to_concept`
   may lie inside or outside `S`; when outside, it is a cross-scope dependency reference (the external
   concept's full context is intentionally not pulled — the model already saw it, or will via that
   concept's own owning step).

All three lists are emitted in the canonical order of §7.

### 5.2 Phase 1 — common block

`context_common(plan, node, shared_concepts, child_level, rev)`:

1. Resolve `node` (a step path or `"plan"`). Its **scope** = `shared_concepts` if supplied, else the
   concepts bound to `node` (all plan concepts when `node == "plan"`).
2. `content` = `[ authoring_template(child_level, tier) , standards(tier(child_level)) ,
   field_schema(child_level) , step_definition(node)? ]` (the baked, plan-independent prose)
   followed by `compile(plan, rev, scope)` (concepts, hrs_fragments, relations). The result is a
   ready-to-send authoring prompt: template prose + DB-derived content, with nothing left for the
   caller to write.
3. Compute `content_hash`, store/return the `common` record. Its `scope_concepts` = `scope`.

### 5.3 Phase 2 — specific block (delta)

`context_specific(plan, common_block_id, concepts)`:

1. Load the referenced common block; let `rev`, `node`, `child_level`, and `common.scope` be its
   fields. **Narrowing check**: every id in `concepts` must be in `common.scope`; otherwise error
   `CONCEPT_OUT_OF_SCOPE`.
2. `full` = `compile(plan, rev, concepts)`.
3. **Delta**: remove from `full` every element already present in the common block —
   - an `mrs_concept` whose `concept_id` is already a concept sub-block in common;
   - an `hrs_fragment` whose `label` is already in common;
   - an `mrs_relation` whose `(from_concept, to_concept, relation_type)` is already in common.
4. `content` = the remaining delta lists, in canonical order. Store/return the `specific` record with
   `common_block_id` set and `scope_concepts = concepts`.

Because the common block already carries the shared scope, a child whose concepts are a subset of the
shared scope produces a near-empty specific block (only what is unique to it), realizing "common once,
specific = delta".

## 6. Commands

All commands are **read-only over plan truth**. Compiling and storing a derived block record is not a
mutation of HRS/MRS/steps and does not advance the head revision. Long compilations may be queue-bound
(return `job_id`, poll status) consistent with existing plan-manager conventions.

### 6.1 `context_compile` (low-level primitive)

Compile a context block from a bare concept set, without common/specific framing.

```text
context_compile(
  plan: string,
  concepts: [C-NNN],
  child_level: 3|4|5 | omitted,      # controls which field_schema/standards to include; omit for none
  include: {standards?, field_schema?, step_definition_of?: node} | omitted,
  revision | cascade_uuid: string | omitted   # default: working state (head + open cascade overlay)
) -> { block_id, hash, revision_uuid, cascade_uuid, blocks: ContentBlock[] }
```

### 6.2 `context_common` (phase 1)

```text
context_common(
  plan: string,
  node: string,                      # parent step path, or "plan"
  child_level: 3|4|5,
  shared_concepts: [C-NNN] | omitted,   # default: concepts bound to `node` (all plan concepts if node=="plan")
  revision | cascade_uuid: string | omitted
) -> { common_block_id, hash, revision_uuid, cascade_uuid, scope_concepts: [C-NNN], blocks: ContentBlock[] }
```

### 6.3 `context_specific` (phase 2)

```text
context_specific(
  plan: string,
  common_block_id: string,
  concepts: [C-NNN]                  # the child's concepts; MUST be a subset of the common block's scope
) -> { block_id, hash, common_block_id, scope_concepts: [C-NNN], blocks: ContentBlock[] }
```

### 6.4 `context_bundle` (convenience: both phases in order)

```text
context_bundle(
  plan: string,
  node: string,
  child_level: 3|4|5,
  children: [ { ref: string, concepts: [C-NNN] } ],   # one entry per child to be authored
  shared_concepts: [C-NNN] | omitted,
  revision | cascade_uuid: string | omitted
) -> {
  common: { common_block_id, hash, scope_concepts, blocks },
  children: [ { ref, block_id, hash, blocks } ]        # each `blocks` is the delta over common
}
```

Runs `context_common` once, then `context_specific` for each child, in that order. Every child's
`concepts` is validated against the common block's scope (narrowing).

### 6.5 `block_get` / `block_list`

```text
block_get(plan: string, block_id: string) -> ContextBlock
block_list(plan: string, node?: string, kind?: "common"|"specific", revision?|cascade_uuid?) -> [ { block_id, hash, kind, node_path, child_level } ]
```

## 7. Determinism and hashing

- **Canonical sub-block order** within `content`: (1) `standards`, (2) `field_schema`, (3)
  `step_definition`, (4) `hrs_fragment` ascending by `position`, (5) `mrs_concept` ascending by
  `concept_id`, (6) `mrs_relation` ascending by `(from_concept, to_concept, relation_type)`.
- **Canonical serialization** for hashing: UTF-8 JSON, object keys sorted lexicographically, no
  insignificant whitespace, arrays in the canonical order above, `created_at` and `block_id`
  **excluded**.
- `content_hash = sha256(canonical_bytes)` (lowercase hex).
- Consequence: for a fixed plan revision, identical inputs give identical `content_hash`; a `common`
  block is byte-identical (same hash) for every child that references it.

## 8. Storage, versioning, lifecycle

- Blocks are **derived cache records** keyed by `(plan_uuid, revision_uuid|cascade_uuid, node_path,
  kind, content_hash)`. Recompiling identical inputs returns the existing record (idempotent).
- A block is bound to the revision/cascade it was compiled against. When the plan's working state
  changes (new cascade revision), previously compiled blocks for the old revision remain valid for
  that old revision; callers requesting the working state get freshly compiled blocks for the new
  revision.
- Blocks are regenerable and may be garbage-collected; losing a block record never loses plan truth.
- `context_specific` requires its `common_block_id` to exist and to belong to the same plan and
  revision/cascade; otherwise error.

## 9. Error taxonomy

Stable string domain codes (consistent with existing plan-manager error style):

- `PLAN_NOT_FOUND` — plan id does not resolve.
- `NODE_NOT_FOUND` — `node` path does not resolve to a step (and is not `"plan"`).
- `CONCEPT_NOT_FOUND` — a supplied concept id is not in the plan MRS.
- `CONCEPT_OUT_OF_SCOPE` — a `context_specific`/`context_bundle` child concept is not within the
  common block's scope (narrowing violation). Details list the offending ids.
- `COMMON_BLOCK_NOT_FOUND` — `common_block_id` does not resolve, or belongs to a different
  plan/revision.
- `INVALID_LEVEL` — `child_level` not in {3,4,5}.
- `REVISION_NOT_FOUND` — explicit `revision` is not a stored revision of the plan.
- `CASCADE_CONFLICT` — supplied `cascade_uuid` is not the plan's open cascade.

## 10. Worked example (G-002 → tacticals)

Plan `workspace_orchestration_refactoring`, global step **G-002** binds concepts
`{C-010, C-011, C-012, C-013, C-014, C-015}`. The orchestrator decomposes it into 3 tacticals and
calls:

```text
context_bundle(plan, node="G-002", child_level=4,
  shared_concepts omitted,                 # → defaults to G-002's own concepts (the inherited scope)
  children=[
    {ref:"session-core",              concepts:["C-010","C-011","C-013"]},
    {ref:"orchestrator-presentation", concepts:["C-012","C-014"]},
    {ref:"identity",                  concepts:["C-015"]}
  ])
```

- **common** (compiled once, written first): `standards(mid)`, `field_schema(4)`,
  `step_definition(G-002)`, and — from the shared scope `{C-010..C-015}` — the six `mrs_concept`
  blocks, the `hrs_fragment` blocks for their `source_labels` (`{t2d6}…{m3y7}`), and the relations
  with `from_concept ∈ {C-010..C-015}`.
- **children[session-core].specific**: `concepts=[C-010,C-011,C-013]` ⊆ scope ✓. Its delta over
  common is **empty** for concepts/fragments/relations already in common — so the specific block is
  minimal, carrying only anything unique not already shared. (In the common-scope case the tactical's
  own material is fully inside common; the specific block mainly narrows the model's attention to its
  three concepts.)

Then, recursively, tactical `session-core` becomes a `node` and its atomic children are authored via
`context_bundle(node="G-002/T-001", child_level=5, children=[{ref, concepts:[…]}, …])`.

## 11. Round-trip with prompt chains

The block types here are the same typed blocks the execution-time `plan_prompt_chain` and the mwps
`context_manager` assemble (HRS fragment, MRS fragment, step blocks, shared-once-referenced). The
compiled block set for an atomic step, ordered `standards → hrs_fragment/mrs_* → step_definition
(global → tactical → atomic)`, MUST reproduce the executable prompt those consumers build for that
step. Implementations should share the compilation core between authoring-time blocks and
execution-time chains.

## 12. Acceptance criteria (as tests)

1. **Concept-only input, deterministic.** `context_compile(plan, ["C-010","C-011"])` returns concept,
   hrs_fragment (for `{t2d6,v8k6,w5g8,u7e9,x7n2,w3m9,c7t2,d1u5,f4c1}`), and relation blocks derived
   solely from the plan; two calls at the same revision return identical `hash`.
2. **Order: common before specific.** `context_specific` errors with `COMMON_BLOCK_NOT_FOUND` when no
   matching common block exists; `context_bundle` produces the common block before any child block.
3. **Specific is a strict delta.** For any child, no `mrs_concept`/`hrs_fragment`/`mrs_relation` in
   its specific block is present in the referenced common block (verified by set intersection = ∅).
4. **Common dedup.** In a `context_bundle` result, the `common` hash is identical across all children,
   and `block_get(common_block_id)` returns exactly one stored record.
5. **Narrowing enforced.** `context_specific(common_of_G002, ["C-020"])` (a concept outside G-002's
   scope) errors `CONCEPT_OUT_OF_SCOPE`.
6. **Working-state.** With an open cascade, blocks reflect uncommitted upper artifacts: after adding a
   concept to a step under a cascade, a bundle requested against that cascade includes it; a bundle
   for `head` does not.
7. **Records, not files.** No file is written and `export_root` is untouched by any command; all
   output is inline JSON.
8. **Read-only.** Head revision and HRS/MRS/steps are unchanged after any sequence of these commands
   (verified by comparing plan status/hashes before and after).
9. **Round-trip.** For a chosen atomic step, the ordered block set equals the block set
   `plan_prompt_chain` emits for that step (same typed blocks, same shared-once-referenced structure).
10. **Idempotent storage.** Calling `context_common` twice with identical inputs returns the same
    `common_block_id` and does not create a second record.
11. **Baked prose is plan-independent.** The `authoring_template`, `standards`, and `field_schema`
    blocks for a given `(child_level, tier)` are byte-identical across two different plans at the same
    template version; no plan-specific prose appears in them. The caller supplies only concept ids and
    the common/specific split — never authoring prose.

## 13. Non-goals

- plan-manager does not author steps or call models; it compiles context. Authored steps return
  through existing `step_create` / `step_update`.
- Not a general document/blob store; blocks are strictly typed derivations of plan data.
- No changes to cascade, gate, or scoring semantics.
- Token counting, 256-token alignment, and padding remain the execution-time concern of
  `plan_prompt_chain` / `context_manager`, reusing the same blocks.
- The selection (which concepts are common vs per-child) is the caller's; this spec does not
  auto-partition concepts.

## 14. Compatibility

Entirely additive: new read-only commands (`context_compile`, `context_common`, `context_specific`,
`context_bundle`, `block_get`, `block_list`) and one new derived record type (`ContextBlock`). No
existing command signature, default, or error condition changes.

## 15. Open decisions for the implementer

1. **Standards source.** Where `standards(tier)` text comes from — static config, a plan-level
   standards field, or doc-store retrieval. Recommendation: a pluggable resolver; ship a config-backed
   default so the command works without doc-store.
2. **Cross-scope relations.** This spec includes relations with `from_concept ∈ S` and renders an
   out-of-scope `to_concept` as a bare reference. If a fuller cross-scope hint is wanted, add an
   optional `include_boundary_concepts` flag that attaches name+definition (not HRS) for external
   endpoints.
3. **Queue vs inline.** Whether compilation is queue-bound; recommendation: inline for single nodes,
   queue-bound for whole-subtree bundles.
4. **GC policy** for derived block records (TTL, or drop on new head revision).
5. **Template storage/versioning.** Where the per-`(child_level, tier)` `authoring_template` (and
   `standards`) live and how they are versioned — recommendation: versioned config assets in
   plan-manager, surfaced as `template_version`, updatable without touching plans, so a template fix
   applies everywhere at once.

## 16. Related requests

- `docs/requests/planmgr_prompt_chain_command_request.md` — `plan_prompt_chain`, the execution-time
  counterpart reusing the same typed-block model.
- `docs/requests/planmgr_working_state_dump_request.md` — the working-state read path these commands
  depend on so bundles reflect an open cascade, not only head.
- `docs/requests/planmgr_file_exchange_interface_request.md` — independent (document ingress).
