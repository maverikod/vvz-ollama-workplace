# Bug: hrs_import real import always fails post-write verification ("re-read text differs from imported text")

**Author:** Vasiliy Zdanovskiy
**email:** vasilyvz@gmail.com
**Date:** 2026-07-06
**Severity:** **blocker** (no HRS can be imported into any plan by any path)
**Affected:** plan_manager 0.1.2 (build ~2026-07-05/06, the build that added `source_text` support to `hrs_import`)

## Table of contents

1. Summary
2. Environment
3. Reproduction matrix
4. Expected vs actual
5. Rollback behavior (works correctly)
6. Analysis (hypotheses)
7. Impact
8. Suggested regression tests
9. Related

## 1. Summary

Every real (`dry_run=false`) call to `hrs_import` fails during post-write verification with:

```
Command execution error: hrs_import verification mismatch: re-read text differs from imported text
```

returned as a job error (JSON-RPC code `-32603`, `native_completed_with_error=false`,
`command_success=false`). `dry_run=true` validation succeeds in every case tried, including the
exact same content that fails on real import, so dry-run masks the defect entirely. This has been
reproduced against both the newly added `source_text` inline path and the pre-existing file-based
`source` path, against three different documents ranging from a full 102-paragraph HRS down to a
single bare paragraph, and against two different plans. The failure is 100% reproducible and
appears unrelated to document content, size, or structure — it points at the verification step
itself, not at anything import-specific to HRS content.

## 2. Environment

- Server: planmgr, reached via MCP-Proxy (`call_server`).
- plan_manager version: 0.1.2, build containing the `source_text` addition to `hrs_import`
  (see Related, item 1).
- All calls below were made 2026-07-05/06 through the MCP proxy, not via host filesystem/shell.

## 3. Reproduction matrix

| # | Plan | Source mode | Content | Size | Result | job_id |
|---|------|-------------|---------|------|--------|--------|
| 1 | hrs-import-probe (`25728725-6f8c-454b-9664-29968c72b3b4`) | `source_text` | Full HRS document: headers, 102 labeled paragraphs, non-binding block | 32 KB | mismatch | `5f8ca010-4968-4206-9024-c70181e36a1a` |
| 2 | hrs-import-probe | `source_text` | Minimal doc: `# Probe` header + two plain-prose paragraphs with labels | small | mismatch | `41ed6115-8e03-4a57-8cc0-876ed957034e` |
| 3 | hrs-import-probe | `source_text` | Single bare paragraph, no header, no trailing `\n`: `` {a1b2} Only paragraph. `` | ~25 bytes | mismatch | `aed2f843-0e37-47a2-9f58-81226a6d37c4` |
| 4 | workspace_orchestration_refactoring | `source` (file) | `workspace_orchestration_source_spec.md` in `/var/planmgr/export`, previously passed file-based `dry_run` | 16546 bytes | mismatch | `703f1e65-713c-4158-9e00-c6d48aad916d` |

`dry_run=true` was run against equivalent/identical content for both `source_text` (case 1's full
document, and previously the file in case 4) and returned `{"dry_run":true,"valid":true}` in every
instance — i.e. validation is not the failing step.

The `hrs-import-probe` plan (`25728725-6f8c-454b-9664-29968c72b3b4`) was created specifically for
this investigation and has been left on the server, in its current (empty/rolled-back) state, for
inspection.

## 4. Expected vs actual

- **Expected:** `hrs_import(dry_run=false, ...)` on content that passed `dry_run=true` validation
  writes the HRS, re-reads it back for verification, finds the re-read text equal to the imported
  text, and returns success (paragraph count / import summary).
- **Actual:** the job always fails at the verification step with "re-read text differs from
  imported text," regardless of source mode (`source` vs `source_text`), content size, or
  structural complexity (full multi-section HRS down to one bare paragraph). Verification never
  succeeds in any trial run.

## 5. Rollback behavior (works correctly)

After each failed import, `para_list` on the target plan returns `{"paragraphs":[]}` — the failed
write is rolled back and plan integrity is preserved. This part of the behavior is correct and is
called out here only to confirm that the bug is isolated to verification, not to the
transaction/rollback machinery.

## 6. Analysis (hypotheses)

The failure reproduces on file-based `source` as much as on `source_text`, and on a single bare
paragraph as much as on a full structured document. This rules out anything specific to
`source_text` handling, to Markdown structure, or to content size — the write path itself and the
verification comparison are the suspects, not the imported content. In rough order of plausibility:

a. **Transaction/revision boundary mismatch (most likely).** The post-write verification re-reads
   the HRS from the head revision while the write is still inside an uncommitted transaction or a
   not-yet-visible new revision, so the comparison is effectively against stale/empty prior state.
   This would explain a 100% failure rate independent of content.
b. **Reconstruction-vs-raw mismatch.** The re-read path reconstructs text from the paragraph model
   rather than comparing against the stored raw text, and the reconstruction is not byte-identical
   to the input (e.g. whitespace/line-ending normalization). Weighed against this: case 3 fails on a
   single unstructured paragraph with no headers, no lists, no non-binding blocks — there is very
   little for a reconstruction step to get wrong, which makes this hypothesis less likely on its
   own but does not rule out a trivial normalization difference (e.g. missing trailing newline).
c. **Verification read resolves the wrong plan/target.** The re-read call in the verification step
   uses an incorrect plan/revision resolution and returns empty or `None`, which would present
   identically to (a).

Recommendation: **check the transaction/revision boundaries around the verification read first** —
i.e. confirm whether the re-read in the verification step is issued against the same
transaction/revision the write just produced, or against a separately-resolved head that hasn't
observed the write yet.

## 7. Impact

This blocks the entire `plan_create` → `hrs_import` → cascade cycle for every plan, via every
supported input path:

- `source_text` (the inline path just added per the request in
  `docs/requests/planmgr_file_exchange_interface_request.md`) cannot complete a real import.
- `source` / `export_root`-based import cannot complete a real import either — this is not a
  regression scoped to the new feature, it affects the pre-existing file path too.

Because `dry_run=true` succeeds in every trial, any CI or acceptance suite that exercises only
dry-run validation will report green while real imports are 100% broken. There is currently no
known working path to get an HRS into a plan.

## 8. Suggested regression tests

Mandatory test, both source modes:

- `hrs_import(dry_run=false, source_text="{aaaa} P.")` on a freshly created plan must return a
  result with `paragraphs=1` (or the equivalent success summary), and a subsequent `para_list` on
  that plan must return exactly 1 binding paragraph.
- The same assertion repeated with `source=<a minimal one-paragraph file in export_root>` to cover
  the file-based path.

Both cases should be run as part of normal CI, not only as a dry-run check, since dry-run alone
does not exercise the code path that is broken.

## 9. Related

- `docs/requests/planmgr_file_exchange_interface_request.md` — the request that added
  `source_text` support to `hrs_import`. Its acceptance criterion #1 ("`hrs_import(source_text=...)`
  performs the same validation and returns the same error taxonomy... as `hrs_import(source=...)`
  on equivalent content") was verified and holds for the **validation** path (`dry_run=true`) only.
  The **write** path (`dry_run=false`) was not covered by that criterion or by any acceptance test
  in that request, and is the subject of this report.
