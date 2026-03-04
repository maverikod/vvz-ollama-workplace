# Step 02: Safe name translation and tool-call registry

**Author:** Vasiliy Zdanovskiy  
**Email:** vasilyvz@gmail.com  

**Scope:** Translate canonical command ids to model-safe names and maintain a registry for resolving tool calls from the model. One step = one file (this doc).

## Goal

- **Safe name rule:** From `Command.ServerId` (e.g. `ollama_chat.ollama-adapter`) produce a name with only `[a-zA-Z0-9_]` (dot, space, hyphen → underscore).
- **Registry:** When building the tool list for a request/session, for each exposed command store **display_name → (command_name, server_id)** so that when the model calls a tool by name we can resolve to the correct command and server.

## Objects

- **SafeNameTranslator:** `to_safe_name(command_id: str) -> str`. Idempotent; only `[a-zA-Z0-9_]` in output; optional collapse of consecutive underscores / max length.
- **ToolCallRegistry:** Mutable mapping display_name → (command_name, server_id). Built when building effective tool list; used by chat flow to execute tool calls. Scope: per request or per session.

## Inputs / outputs

- **Input (translator):** Canonical command id string.
- **Output (translator):** Safe name string.
- **Input (registry):** Sequence of (display_name, command_name, server_id) when building tool list.
- **Output (registry):** Resolution: given display_name, return (command_name, server_id) or raise.

## Acceptance criteria

- Examples: `ollama_chat.ollama-adapter` → `ollama_chat_ollama_adapter`; `chunk.svo-chunker` → `chunk_svo_chunker`.
- Registry correctly resolves every name that was registered; unknown name raises or returns a clear error.
- No dependency on config or proxy; pure translation and in-memory registry.

## References

- Main plan: [§1.5 Safe command name translation and registry](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#15-safe-command-name-translation-and-registry).
- Objects and diagrams: [00_objects_and_diagrams.md](00_objects_and_diagrams.md) (SafeNameTranslator, ToolCallRegistry).
- Prev: [step_01_config_and_policy.md](step_01_config_and_policy.md). Next: [step_03_command_discovery.md](step_03_command_discovery.md). Used by step 06 and chat flow.

## Success metrics

- **Step-specific:** `ollama_chat.ollama-adapter` → `ollama_chat_ollama_adapter`; `chunk.svo-chunker` → `chunk_svo_chunker`; registry resolves every registered display_name to (command_name, server_id); unknown name raises or returns clear error.
- **Standard verification:** No incomplete code, TODO, ellipsis, or syntax issues; no `pass` outside exceptions; no `NotImplemented` outside abstract methods; no deviations from [RULES](../../RULES.md) or plan. After code: `code_mapper -r src`; `mypy src`, `flake8 src tests`, `black src tests` (fix all).

## Comparative analysis vs existing code

| Aspect | Existing | To change | To add |
|--------|----------|-----------|--------|
| Tool names | `tools.py`: fixed names `list_servers`, `call_server`, `help` | Nothing in this step | SafeNameTranslator: to_safe_name(command_id) → [a-zA-Z0-9_]; ToolCallRegistry: display_name → (command_name, server_id) |
| Chat flow | `chat_flow.py`: _run_tool branches on tool_name string | — | Later (step 06): resolve tool_name via ToolCallRegistry to (command, server_id) and call proxy |

## Dependencies

- None. Step 06 and chat flow use these.

## Deliverable

- SafeNameTranslator (function or class); ToolCallRegistry (class). Unit tests for translation and registry resolution.
