# Interface Request: on-demand, round-trippable dump of a plan's live working state (open cascade included)

**Author:** Vasiliy Zdanovskiy
**email:** vasilyvz@gmail.com
**Date:** 2026-07-06
**Requesting project:** mwps
**Severity:** durability gap (working state cannot be safely backed up to disk)

## Table of contents

1. Problem statement
2. Evidence: the 2026-07-06 dump attempt
3. Why the current behavior is unacceptable
4. Proposed changes
5. Interface sketch
6. Acceptance criteria
7. Non-goals
8. Compatibility
9. Notes / related requests

## 1. Problem statement

plan-manager offers no way to write a **clean, self-consistent, re-importable dump of a plan's
current working state to disk at an arbitrary moment**. Concretely, while a cascade is open, the
plan's live truth (its MRS — concepts and relations authored under that open cascade) exists only
in the server database and cannot be exported to a layout that `plan_import` will accept.

The only file-export command, `plan_export`, has two modes and neither covers the working state:

- `plan_export` with no `revision` exports the **head** revision. Head is clean and
  round-trippable, but it does **not** contain anything authored under an open (uncommitted)
  cascade. For a plan whose MRS lives entirely in an open cascade, the head dump contains the HRS
  and **zero concepts**.
- `plan_export` with `revision=<open-cascade tip>` **does** include the cascade's concepts and
  relations, but it emits a layout in which the **HRS is duplicated** — every HRS label appears
  twice — so `plan_import` rejects it as `IMPORT_INVALID`.

There is therefore no command that produces a dump which is simultaneously (a) complete with
respect to the live working state and (b) valid for re-import. A plan under active authoring
cannot be backed up to disk.

This matters because plan-manager is periodically restarted/updated (the server flapped and was
updated during this very session). If an update ever clears the database, the working MRS — in our
case **38 concepts + 63 relations** sitting in an open cascade — is unrecoverable, because it was
never expressible as a valid on-disk artifact.

## 2. Evidence: the 2026-07-06 dump attempt

Plan `workspace_orchestration_refactoring`
(uuid `e271ef77-0e62-4450-8bfa-f253659a0534`), HRS = 102 binding paragraphs committed at head,
MRS = 38 concepts + 63 relations authored under **open cascade** `b3210dff-…` (uncommitted; the
plan has no steps yet, so the mechanical gate is red and `cascade_commit` refuses).

Observed, all via plan-manager MCP calls only:

1. `plan_export(plan)` → `{root: /var/planmgr/export/workspace_orchestration_refactoring,
   files: 2, revision: "head"}`. `plan_import(source=..., dry_run=true)` → **`valid: true`**.
   But this head layout contains **no concepts** — they are in the open cascade, not in head.
2. `plan_export(plan, revision="72bacd3d-…")` (the open cascade's tip revision — accepted, not
   `REVISION_NOT_FOUND`) → `{files: 2, revision: "72bacd3d-…"}`. `plan_import(dry_run=true)` on
   the resulting layout → **`IMPORT_INVALID`**, with 102 issues of the form
   `hrs: duplicate label: a1k2` … `hrs: duplicate label: u4d8` — i.e. the exported HRS carries
   each of the 102 labels **twice** (204 label lines).
3. Control: re-running the head export and re-validating → `valid: true` again. This proves
   `plan_export` overwrites its target files cleanly (no stale-file accumulation); the duplication
   in step 2 is intrinsic to exporting an open-cascade revision, not an artifact of repeated runs.

Net: the only dump that contains the live MRS is not re-importable, and the only re-importable
dump omits the live MRS.

## 3. Why the current behavior is unacceptable

- **Active work is undurable.** Between opening a cascade and committing it, the authored MRS
  cannot be persisted to disk in a recoverable form. For a top-down plan, that window spans the
  entire MRS-authoring and step-authoring effort — potentially the bulk of the plan's construction.
- **Backups must not depend on reaching a green gate.** Today the only path to a clean, complete,
  re-importable dump is `cascade_commit`, which requires a green mechanical gate, which requires
  the full step tree to already exist. Requiring a *finished* plan before a *backup* is possible
  is backwards: backups are most needed precisely while the plan is unfinished.
- **The cascade-revision export looks buggy.** Emitting the HRS twice (base head + cascade overlay)
  is almost certainly unintended; a revision export should render one coherent state, not
  concatenate two HRS sources.
- **It defeats the point of routine dumps.** mwps needs to snapshot plan state to disk regularly
  (especially around server updates) as a safety net. A snapshot mechanism that silently excludes
  in-flight work, or produces an un-importable file, provides false assurance.

## 4. Proposed changes

Either change below solves the problem; they are complementary.

1. **Fix open-cascade revision export (bug fix).** `plan_export(revision=<cascade tip>)` must
   render the effective state at that revision as a single coherent layout — in particular, the
   HRS must appear exactly once. The resulting layout must satisfy `plan_import(dry_run=true) →
   valid:true`. This is the smaller change and, on its own, makes "dump the working state" a
   matter of exporting the open cascade's tip revision.

2. **Add a first-class working-state snapshot command (feature).** A new read-only command,
   e.g. `plan_snapshot(plan)`, that renders the plan's **effective working state** — head with the
   open cascade overlaid, or plain head when no cascade is open — into the standard file layout
   under `export_root`, deduplicated and self-consistent, with **no gate or commit precondition**.
   It succeeds at any moment in the plan's lifecycle. This gives callers a single, intention-
   revealing "dump everything as it is right now" operation without having to know about revision
   ids or cascade internals.

Both are additive and read-only over plan truth (no database mutation), consistent with the
existing `plan_export` contract.

## 5. Interface sketch

```
# Fix (change 1): same signature, corrected rendering
plan_export(
  plan: string,
  revision: string | omitted   # when it is an open cascade's tip, HRS is emitted once, not twice
) -> { root, files, revision }   # layout MUST pass plan_import(dry_run=true)

# Feature (change 2): new command
plan_snapshot(
  plan: string
) -> {
  root: string,            # export_root/<plan-name> (standard layout)
  files: int,
  based_on_revision: string,   # head revision the snapshot reflects
  cascade_uuid: string | null, # the open cascade overlaid, or null if none open
  importable: true             # guaranteed to satisfy plan_import(dry_run=true)
}
# Read-only; no gate, no commit, no cascade state required. Queue-bound like plan_export.
```

## 6. Acceptance criteria

1. For a plan with an open cascade, a dump of the working state (via fixed `plan_export(revision=
   <cascade tip>)` or via `plan_snapshot`) yields a layout in which **each HRS label appears
   exactly once** (no `duplicate label` issues).
2. `plan_import(source=<that layout>, dry_run=true)` returns `valid: true`.
3. That layout contains **all** MRS entities present in the working state — every concept and
   every relation authored under the open cascade (for the reference plan: 38 concepts, 63
   relations), plus the full HRS (102 paragraphs).
4. The dump succeeds with **no green-gate and no commit precondition**: it works while the
   mechanical gate is red and no steps exist.
5. Round-trip fidelity: importing the dump into a fresh plan (`plan_import(dry_run=false)`)
   reproduces byte-identical HRS (`hrs_export`) and identical `concept_list` / `relation_list`
   to the source plan's working state.
6. The operation is read-only: it never mutates the source plan, its head, or its open cascade.
7. When no cascade is open, `plan_snapshot` is equivalent to `plan_export` of head, and both
   remain `valid` for import (no regression to today's working head export).
8. Backward compatibility: existing `plan_export(plan)` (head) callers observe no change.

## 7. Non-goals

- Not proposing to auto-commit the cascade or to change gate/scoring semantics — a snapshot is a
  read-only rendering of current state, not a state transition.
- Not proposing a new persistence backend or a general file-versioning product; the snapshot
  reuses the existing standard layout and `export_root`.
- Not proposing scheduling/retention policy for dumps; cadence and retention are the caller's
  concern (mwps will drive periodic snapshots itself).

## 8. Compatibility

Change 1 corrects an invalid output of an existing command (a plan that previously produced an
un-importable layout will now produce an importable one); no valid existing behavior changes.
Change 2 is an entirely new, additive command. No existing signature, default, or error condition
changes for current callers.

## 9. Notes / related requests

Context: mwps treats the plan-manager database as the source of truth for plan structure and needs
to snapshot it to disk regularly — as an ongoing durability practice, not a one-off — especially
around plan-manager restarts and updates. See also
`docs/requests/planmgr_file_exchange_interface_request.md` (getting documents *into* export_root)
and `docs/requests/planmgr_hrs_import_verification_bug.md`; this request is the *export* side of
the same durability story and is independent of both.
