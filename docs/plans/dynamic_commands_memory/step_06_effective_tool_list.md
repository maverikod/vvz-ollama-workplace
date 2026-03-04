# Step 06: Effective tool list builder

**Author:** Vasiliy Zdanovskiy  
**Email:** vasilyvz@gmail.com  

**Scope:** Merge config policy, config lists, and session lists to produce the effective list of tools for a session; resolve display names (alias or safe name) and build ToolCallRegistry. One step = one file (this doc).

## Goal

- **Effective tool list** = merge(config, session): apply config policy and config lists first, then session allowed/forbidden. Config forbidden can never be overridden by session.
- **Dedupe by command name:** When the same command name appears on several servers (e.g. Instrument1.ServerA, Instrument1.ServerB), only the **first occurrence** (by discovery order) is kept. So the model sees one tool per command name.
- **Model sees display_name = command name only** (e.g. Instrument1, Instrument2, Instrument3). No server suffix. Descriptions come from the schema of the chosen (first) occurrence.
- **On call:** The code resolves display_name to (command_name, server_id) via ToolCallRegistry and calls that server directly; the model never sees or chooses the server.

## Objects

- **EffectiveToolListBuilder:** build(session, commands_policy_config, discovered_commands, alias_registry, safe_name_translator) -> (list of tool definitions for representation, ToolCallRegistry).

## Inputs / outputs

- **Input:** Session (model, allowed_commands, forbidden_commands); CommandsPolicyConfig; list of (CommandId, CommandSchema) from discovery; CommandAliasRegistry; SafeNameTranslator.
- **Output:** (tool_list_canonical, ToolCallRegistry). tool_list_canonical is what ContextRepresentation.serialize_tools() will receive; ToolCallRegistry maps every display_name used to (command_name, server_id).

## Acceptance criteria

- Config forbidden: if a command is in config forbidden_commands, it never appears in the effective list.
- Under deny_by_default, only commands in config allowed_commands (minus forbidden) can appear; session can only further restrict. Under allow_by_default, all discovered minus config forbidden; session can restrict.
- Every tool in the list has a unique display_name registered in ToolCallRegistry. If an alias (or safe name) would duplicate an already-registered display_name for this build, log warning and use safe name for the duplicate, or treat as config error and fail the build.
- Adding a config-forbidden command to session allowed does not make it appear (session cannot override config).

## References

- Main plan: [§1.4 Config: allowed / forbidden commands and policy](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#14-config-allowed--forbidden-commands-and-policy), [§1.9 Per-session commands](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#19-per-session-commands-add--remove-priority-of-config-over-session), [§1.10 Summary (commands)](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#110-summary-commands).
- Objects and diagrams: [00_objects_and_diagrams.md](00_objects_and_diagrams.md), [sequence: build effective tool list](00_objects_and_diagrams.md#3-diagram-build-effective-tool-list-and-serialize-for-model).
- Prev: [step_05_session_store.md](step_05_session_store.md). Next: [step_07_context_representation_base.md](step_07_context_representation_base.md). Depends on steps 01–05.

## Success metrics

- **Step-specific:** Config forbidden ⇒ command never in list; deny_by_default ⇒ only config allowed minus forbidden (session can only restrict); allow_by_default ⇒ all discovered minus config forbidden; every tool has unique display_name in ToolCallRegistry; config-forbidden in session allowed does not appear.
- **Standard verification:** No incomplete code, TODO, ellipsis, or syntax issues; no `pass` outside exceptions; no `NotImplemented` outside abstract methods; no deviations from [RULES](../../RULES.md) or plan. After code: `code_mapper -r src`; `mypy src`, `flake8 src tests`, `black src tests` (fix all).

## Comparative analysis vs existing code

| Aspect | Existing | To change | To add |
|--------|----------|-----------|--------|
| Tool list | `tools.py` get_ollama_tools() returns fixed list | Chat flow will later use builder output instead of get_ollama_tools() when dynamic path is enabled | EffectiveToolListBuilder: merge policy + config + session; resolve alias or safe name; build ToolCallRegistry; output (tool_list_canonical, ToolCallRegistry) |
| Chat flow | `chat_flow.py` uses get_ollama_tools(), _run_tool by name | Future: accept session_id; resolve tool name via registry; call proxy by (command, server_id) | — |

## Dependencies

- Steps 01, 02, 03, 04, 05.

## Deliverable

- EffectiveToolListBuilder class; integration with policy, discovery, alias registry, safe name. Unit tests with mocked session, config, discovery, alias registry.
