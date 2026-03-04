# Step 04: Command alias registry per model

**Author:** Vasiliy Zdanovskiy  
**Email:** vasilyvz@gmail.com  

**Scope:** Store and look up per-model (or per representation type) display names for commands. When building the tool list for a session, use alias if defined, else safe name. One step = one file (this doc).

## Goal

- Support **aliases per model** so that the same logical command can be exposed under different names to different models (e.g. to avoid reserved words or provider quirks).
- When building the tool list for a session: for each command, look up alias for the session’s model (or representation type); if present use it as the tool name sent to the model; otherwise use safe name from step 02.
- The **reverse lookup** (model’s tool call → command + server_id) must use the **actual name sent to the model** (alias or safe name); ToolCallRegistry is built with that name (step 02 + 06).

## Objects

- **CommandAliasRegistry:** Mapping (command_id, model_id) → display_name. Optional (config or DB). Method: `get_display_name(command_id, model_id) -> Optional[str]`. If None, caller uses safe name.

## Inputs / outputs

- **Input:** command_id, model_id (or representation_type_id).
- **Output:** display_name or None (meaning use safe name).
- Config/storage: e.g. YAML section or table (command_id, model_or_type, display_name).

## Acceptance criteria

- If no alias is configured for (command_id, model), returns None and downstream uses safe name.
- If alias is configured, that exact name is used for the tool and registered in ToolCallRegistry for resolution.
- **Uniqueness:** Alias must be unique per (session, model) for the effective tool list. If two command_ids resolve to the same display_name for a model, treat as configuration error: log warning and use safe name for the duplicate (or fail the build — implementation choice). Document in step 06 when building the list.
- Storage format and location documented; default: no aliases (all use safe names).

## References

- Main plan: [§1.6 Command registry and aliases per model](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#16-command-registry-and-aliases-per-model).
- Objects and diagrams: [00_objects_and_diagrams.md](00_objects_and_diagrams.md) (CommandAliasRegistry), [sequence: build effective tool list](00_objects_and_diagrams.md#3-diagram-build-effective-tool-list-and-serialize-for-model).
- Prev: [step_03_command_discovery.md](step_03_command_discovery.md). Next: [step_05_session_store.md](step_05_session_store.md). Step 06 uses this when building the effective tool list.

## Success metrics

- **Step-specific:** get_display_name(command_id, model_id) returns None ⇒ downstream uses safe name (step 02); if alias configured, that name is used and registered in ToolCallRegistry; storage format and default (no aliases) documented.
- **Standard verification:** No incomplete code, TODO, ellipsis, or syntax issues; no `pass` outside exceptions; no `NotImplemented` outside abstract methods; no deviations from [RULES](../../RULES.md) or plan. After code: `code_mapper -r src`; `mypy src`, `flake8 src tests`, `black src tests` (fix all).

## Comparative analysis vs existing code

| Aspect | Existing | To change | To add |
|--------|----------|-----------|--------|
| Tool names | `tools.py`: fixed names only | — | CommandAliasRegistry: (command_id, model_id) → display_name; config or DB; default no aliases |
| Tool list build | Not present (fixed tools) | — | Step 06 will call get_display_name(session.model); alias or safe name → register in ToolCallRegistry |

## Dependencies

- Step 02 (safe name). Step 06 uses this when building the effective tool list.

## Deliverable

- CommandAliasRegistry interface and at least one implementation (e.g. config-based). Unit tests.
