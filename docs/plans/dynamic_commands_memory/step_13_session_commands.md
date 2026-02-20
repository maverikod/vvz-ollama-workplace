# Step 13: Session-init and add/remove command to session

**Author:** Vasiliy Zdanovskiy  
**Email:** vasilyvz@gmail.com  

**Scope:** Adapter commands: (1) session init — create session, return session_id; (2) add command to session; (3) remove command from session. Enforce config priority: adding a config-forbidden command is rejected and logged. One step = one file (this doc).

## Goal

- **SessionInitCommand:** Adapter command (e.g. `session_init` or `start_session`). **Request format: JSON.** Fields: **command name** (adapter command identifier), **session identifier** (absent in request; returned in response), **parameters** — dictionary whose keys are session record/DB fields (e.g. `model`, `allowed_commands`, `forbidden_commands`, `standards`, `session_rules`). Creates session via SessionStore.create(parameters); returns session_id (UUID4) in response body, e.g. `{ "session_id": "<uuid4>" }`. Session may be created without model; model must be set before first context build or chat (via SessionUpdateCommand).
- **SessionUpdateCommand:** Updates session attributes. Parameters: session_id, optional model, optional allowed_commands, optional forbidden_commands. Used to set or change the session model (context window and representation type). If context build or chat is called with session.model unset, return a clear error ("session model not set").
- **AddCommandToSessionCommand:** Adds a command identifier to the session’s allowed list (or removes from session’s forbidden list). If the command is in **config** forbidden_commands, do **not** add and **log an error**; do not update session store for that command.
- **RemoveCommandFromSessionCommand:** Removes the command from the session’s allowed list or adds it to the session’s forbidden list so it is no longer available in that session.
- All requests that participate in the same dialogue must include session_id (mandatory). Session-init is the only way to obtain a new session_id.

## Objects

- **SessionInitCommand:** Executes SessionStore.create(attrs); returns { session_id: uuid4 } (or similar). Registers as adapter command.
- **SessionUpdateCommand:** Parameters: session_id, optional model, optional allowed_commands, optional forbidden_commands. Calls SessionStore.update(session_id, attrs). Registers as adapter command.
- **AddCommandToSessionCommand:** Parameters: session_id, command_id. Checks config forbidden_commands; if command_id in config forbidden, log error and return error response; else update session (add to allowed or remove from forbidden). Registers as adapter command.
- **RemoveCommandFromSessionCommand:** Parameters: session_id, command_id. Updates session (remove from allowed or add to forbidden). Registers as adapter command.

## Inputs / outputs

- **Input (init):** Optional model, optional lists. **Output:** session_id (UUID4).
- **Input (update):** session_id, optional model, optional allowed_commands, optional forbidden_commands. **Output:** success or error.
- **Input (add):** session_id, command_id. **Output:** success or error (e.g. "command X is forbidden by config and cannot be added to session").
- **Input (remove):** session_id, command_id. **Output:** success.

## Acceptance criteria

- Session init always returns a new session_id; session is persisted with model (if provided) and empty or provided lists. Session may be created without model; model must be set (via session update or first request) before context build or chat; otherwise return clear error.
- Add command: config forbidden overrides; session store is not updated when command is config-forbidden; client receives clear error and it is logged.
- Remove command: session is updated so that the command is no longer in the effective tool list for that session (effective list is computed in step 06).

## References

- Main plan: [§1.9 Per-session commands](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#19-per-session-commands-add--remove-priority-of-config-over-session), [§4.1 Session](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#41-session), [§3.5.2 Session store (schema)](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#352-session-store-session-entity). SessionUpdateCommand: main plan Object model table and §1.8.
- Objects and diagrams: [00_objects_and_diagrams.md](00_objects_and_diagrams.md) (SessionInitCommand, SessionUpdateCommand, AddCommandToSessionCommand, RemoveCommandFromSessionCommand), [diagram: session init and model change](00_objects_and_diagrams.md#7-diagram-session-init-and-model-change).
- Prev: [step_12_call_stack_and_depth.md](step_12_call_stack_and_depth.md). Depends on steps 01, 05. Step 06 uses session data.

## Success metrics

- **Step-specific:** Session init returns new session_id (UUID4); session persisted with model and lists; add command: if config forbidden ⇒ do not add, log error, return error to client; remove command: session updated so command not in effective list.
- **Standard verification:** No incomplete code, TODO, ellipsis, or syntax issues; no `pass` outside exceptions; no `NotImplemented` outside abstract methods; no deviations from [RULES](../../RULES.md) or plan. After code: `code_mapper -r src`; `mypy src`, `flake8 src tests`, `black src tests` (fix all).

## Comparative analysis vs existing code

| Aspect | Existing | To change | To add |
|--------|----------|-----------|--------|
| Commands | `ollama_chat_command.py`: OllamaChatCommand, no session_id | Future: chat command may require session_id; session created via SessionInitCommand | SessionInitCommand; SessionUpdateCommand (set model, update lists); AddCommandToSessionCommand (reject if config forbidden); RemoveCommandFromSessionCommand |
| Adapter | Commands registered in adapter | Register new commands (session_init, add_command_to_session, remove_command_from_session) | — |
| Config | CommandsPolicyConfig (step 01) | — | Add/remove use config forbidden_commands to reject add |

## Dependencies

- Steps 01 (CommandsPolicyConfig), 05 (SessionStore). Adapter command registration (existing). Step 06 uses session data when building effective tool list.

## Deliverable

- SessionInitCommand, SessionUpdateCommand, AddCommandToSessionCommand, RemoveCommandFromSessionCommand; registration in adapter. **Session-init format:** JSON request with **command name**, **parameters** (dict of session-record fields: model, allowed_commands, forbidden_commands, standards, session_rules, etc.); response includes **session_id**. Integration tests or unit tests with mocked store and config.
