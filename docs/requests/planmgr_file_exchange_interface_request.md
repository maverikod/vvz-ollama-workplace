# Interface Request: file-exchange path for plan-manager import commands

**Author:** Vasiliy Zdanovskiy
**email:** vasilyvz@gmail.com
**Date:** 2026-07-05
**Requesting project:** mwps
**Severity:** interface gap (workaround exists but is unacceptable)

## Table of contents

1. Problem statement
2. Evidence: the 2026-07-05 incident
3. Why the current workaround is unacceptable
4. Proposed changes
5. Interface sketch
6. Acceptance criteria
7. Non-goals
8. Compatibility
9. Notes / related requests

## 1. Problem statement

plan-manager's `hrs_import` (and `plan_import`) accept only a bare file name, which the server
resolves under its own configured `export_root`; they accept no path, and no inline content.
There is, however, no plan-manager API that places a file into `export_root` in the first
place. The mcp_proxy_adapter built-in transfer commands — `transfer_upload_begin`,
`transfer_upload_status`, `transfer_upload_complete` — are present on the plan-manager server,
but a completed upload session is not connected to `export_root` in any way: there is no bridge
command that takes a finished transfer and stages it where `hrs_import`/`plan_import` can see
it.

The practical consequence: as of this writing, the only working way to get a document into
plan-manager is direct host-filesystem access to the machine plan-manager runs on. That
contradicts the ecosystem principle that inter-service interaction goes through MCP Proxy APIs,
not ad hoc host access.

## 2. Evidence: the 2026-07-05 incident

Delivering a single 17 KB HRS markdown document
(`docs/plans/workspace_orchestration_refactoring/source_spec.md`) into plan-manager required,
in order:

1. Discovering the physical host running the plan-manager server (`192.168.254.26`) — nothing
   in plan-manager's own API surface reveals this.
2. Obtaining root SSH access via a *separate* service (mcp-terminal's `terminal_host_exec`),
   because plan-manager itself has no file-placement command.
3. Reading `/etc/planmgr/config.json` on that host to learn the value of
   `plan_manager.export_root` (`/var/planmgr/export`) — again, not discoverable through the
   plan-manager API.
4. Writing the file via `python3 -c "base64.b64decode(...)"` invoked once per chunk, in 12
   chunks of 2000 characters each, with a per-chunk SHA-256 verification step, because a
   single-shot transfer of the full payload silently corrupted the content.
5. Only then could `hrs_import(source="source_spec.md")` succeed.

This is the entire delivery path for a *text document under 20 KB*. There is no plan-manager
API involved anywhere in steps 1–4 — every one of them is a workaround around the absence of
one.

## 3. Why the current workaround is unacceptable

- **Requires root on the plan-manager host.** A document-import operation should never need
  host-level privileges; it is a data-plane operation, not an administrative one.
- **Requires a second, unrelated service** (mcp-terminal) to do something that is squarely
  plan-manager's own responsibility (getting a file into its own `export_root`).
- **Breaks the "everything through MCP Proxy APIs" principle** that governs how mwps and its
  peer services are meant to interact.
- **Fragile in practice, not just in principle.** The single-shot transfer path silently
  corrupted the payload; only manual chunking with per-chunk checksums produced a correct
  result. This is not a reasonable steady-state operating procedure for routine plan-sync
  traffic.
- **Does not scale.** mwps intends to keep plan documents in git and sync them into
  plan-manager routinely, not as a one-off rescue operation. A procedure that takes host root
  access and manual chunk-by-chunk verification cannot be the normal path for that.

## 4. Proposed changes

Two complementary changes are proposed; **either one alone unblocks** the mwps workflow, but
both together cover both delivery shapes mwps needs (small inline text, and larger archives).

1. **Inline source for `hrs_import`.** Extend `hrs_import` with a new, mutually exclusive
   alternative to the existing `source` parameter: `source_text` (string — the full Markdown
   content of the HRS document). HRS documents are, by nature, tens of kilobytes at most, and
   fit trivially inside a JSON-RPC request body. All existing validation, `dry_run` behavior,
   and cascade/admission semantics apply unchanged, operating on the supplied text instead of a
   file read from `export_root`. Symmetrically, `hrs_export` could gain a `return_text: true`
   flag that returns content inline instead of writing to `export_root`, closing the loop for
   round-tripping.

2. **Transfer-to-export-root bridge, for `plan_import` and large archives.** A new command,
   `export_upload_save(transfer_id, filename)`, that promotes the staged payload of a completed
   `transfer_upload_*` session into `export_root` under a bare `filename`, subject to the same
   path-safety rules already implied by `hrs_import`/`plan_import` (no `/`, no `\`, no `..`).
   This mirrors a pattern already implemented and proven elsewhere in the ecosystem: Code
   Analysis Server exposes `transfer_upload_*` plus a `project_file_transfer_upload_save`
   bridge command for exactly this purpose. plan-manager would gain the equivalent, scoped to
   `export_root`.

## 5. Interface sketch

```
hrs_import(
  source: string | omitted,        # existing: bare filename under export_root
  source_text: string | omitted,   # new: inline Markdown content
  dry_run: bool = true,            # unchanged default and semantics
  ... existing parameters unchanged
)
# exactly one of {source, source_text} must be present; both or neither is a parameter error.

export_upload_save(
  transfer_id: string,   # id of a transfer_upload_* session already in COMPLETE state
  filename: string       # bare name to stage under export_root; no path separators, no '..'
) -> { filename: string, size_bytes: int, sha256: string }
```

## 6. Acceptance criteria

1. `hrs_import(source_text="...")` performs the same validation and returns the same error
   taxonomy (e.g. `IMPORT_INVALID`) as `hrs_import(source="...")` on equivalent content.
2. `hrs_import` defaults to `dry_run=true` identically regardless of whether `source` or
   `source_text` was supplied.
3. Supplying both `source` and `source_text` in the same call is a parameter error; supplying
   neither is also a parameter error. Neither silently picks one over the other.
4. `export_upload_save` rejects a `transfer_id` whose upload session is not in a completed
   state, with an explicit error (no partial or best-effort staging).
5. `export_upload_save` rejects `filename` values containing `/`, `\`, or `..`, with an explicit
   parameter error — the same path-safety class of check `hrs_import`/`plan_import` already
   apply to their `source` filename.
6. Byte-for-byte integrity of a file staged via `export_upload_save` is verifiable through the
   existing transfer-API checksum mechanism (i.e., the checksum recorded at
   `transfer_upload_complete` matches the staged file's checksum) — no new checksum mechanism
   needs to be invented.
7. The full cycle `plan_create` → `hrs_import` → cascade can be completed by an mwps agent
   using only plan-manager MCP calls, with no host-filesystem or host-shell access of any kind.
8. Backward compatibility: existing callers using only `source` (the current parameter) observe
   no change in behavior, defaults, or error conditions.

## 7. Non-goals

- Not proposing changes to plan-manager's cascade, admission, or gate-scoring semantics — those
  apply identically regardless of how the source bytes arrived.
- Not proposing that `export_upload_save` become the only path into `export_root` — direct
  filesystem placement by trusted operators, where legitimate, is unaffected.
- Not proposing a general-purpose file-transfer product inside plan-manager; `export_upload_save`
  is deliberately scoped to promoting an already-completed transfer session into `export_root`,
  reusing the transfer machinery that already exists on the server.

## 8. Compatibility

Both proposed changes are additive. `source_text` is a new, optional, mutually exclusive
alternative to `source` on `hrs_import`; `export_upload_save` is an entirely new command. No
existing command signature, default, or error condition changes for callers that do not use the
new parameters/command.

## 9. Notes / related requests

Context: mwps maintains its plan documents under git
(`docs/plans/workspace_orchestration_refactoring/`) and synchronizes them into plan-manager as
part of routine plan-authoring workflow — this is not a one-off migration but an ongoing,
repeated operation, which is why the host-filesystem workaround in §2–3 is unacceptable as a
standing procedure.

A related, separate request to the plan-manager team already exists:
`docs/requests/planmgr_prompt_chain_command_request.md` (proposing a `plan_prompt_chain`
command). That request and this one are independent — the prompt-chain command changes what
plan-manager can *return* for a green-gated plan, whereas this request changes how a plan's
source documents get *in* to plan-manager in the first place.
