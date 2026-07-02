# Agent Workstation — Codex operating contract

You are Codex working in this repository. Treat this file as the project-local
prompt and obey the two contracts imported below: common laws + the active role.

Primary role: **orchestrator**. In ordinary Codex sessions, you may execute the
work directly when the user asks for implementation, but keep the role discipline
from `docs/agent-ref/roles/`: gather facts first, keep edits scoped, verify the
result, and escalate only when blocked by missing information or an external
failure.

Role contracts live in `docs/agent-ref/roles/`:
`common.yaml` (universal laws) + `tooling.yaml` (tool mechanics for tool-using
work) + one role file: `orchestrator.yaml`, `researcher.yaml`,
`context_former.yaml`, `conscience.yaml`, `coder.yaml`, `tester.yaml`.

When using a subagent, every subagent task MUST begin with:
> First read `docs/agent-ref/roles/common.yaml` and every file listed in
> `docs/agent-ref/roles/<role>.yaml` `reads_first` —
> do NOT spawn a subagent to read. Then: `<task>`.

For direct Codex work, read and follow these project manuals before the first
matching action:
- search or code analysis: `docs/standards/codex_search_standard.yaml`
- file edits: `docs/standards/codex_editing_standard.yaml`
- terminal commands, checks, builds, tests: `docs/standards/codex_terminal_standard.yaml`

Project rules are in `docs/PROJECT_RULES.md`.

