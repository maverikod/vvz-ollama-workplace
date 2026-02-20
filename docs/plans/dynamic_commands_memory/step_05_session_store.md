# Step 05: Session entity and SessionStore

**Author:** Vasiliy Zdanovskiy  
**Email:** vasilyvz@gmail.com  

**Scope:** Define the Session entity and the SessionStore persistence interface; implement at least one store (e.g. SQLite or Redis-backed). One step = one file (this doc).

## Goal

- **Session** entity: id (UUID4), model (required), allowed_commands, forbidden_commands, created_at, and any other attributes (e.g. user_id, metadata). Per main plan §3.5.2, **standards** and **session_rules** are passed at session create and stored in **local Redis** (keyed by session_id); they can be updated; the Session entity or store may accept them in create/update attrs.
- **SessionStore** interface: get(session_id), create(attributes), update(session or partial attributes).
- Session is created when session-init is called (step 13); all chat/context requests supply session_id and load session from store.
- Context window size is derived from session.model (see main plan §4.4).

## Objects

- **Session:** Immutable or mutable entity with the fields above. Model is required.
- **SessionStore:** Interface: get(session_id) -> Optional[Session]; create(attrs) -> Session; update(session_id, attrs) -> Session. Implementations: e.g. SessionStoreSqlite, SessionStoreRedis.

## Inputs / outputs

- **Input (create):** Attributes dict including model (optional at create; can be set later via SessionUpdateCommand), allowed_commands, forbidden_commands. If model is not set, context build or chat must not proceed until model is set (return clear error).
- **Output (create):** Session with generated id (UUID4).
- **Input (get):** session_id.
- **Output (get):** Session or None.

## Acceptance criteria

- Session always has id and model (model may be set at create or via update).
- Config forbidden_commands is not stored in session; it is applied in config layer (step 06). Session only stores session-level allowed/forbidden.
- Store implementation is configurable (e.g. type and connection in config).

## References

- Main plan: [§1.8 Session store (database)](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#18-session-store-database), [§4.1 Session](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#41-session), [§3.5.2 Session store (Session entity) — schema reference](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#352-session-store-session-entity).
- Objects and diagrams: [00_objects_and_diagrams.md](00_objects_and_diagrams.md) (Session, SessionStore), [diagram: session init and model change](00_objects_and_diagrams.md#7-diagram-session-init-and-model-change).
- Prev: [step_04_command_aliases.md](step_04_command_aliases.md). Next: [step_06_effective_tool_list.md](step_06_effective_tool_list.md). Steps 06, 10, 13 depend on SessionStore.

## Success metrics

- **Step-specific:** Session has id (UUID4) and model (required); store interface get/create/update; config forbidden_commands not in session; store implementation configurable.
- **Standard verification:** No incomplete code, TODO, ellipsis, or syntax issues; no `pass` outside exceptions; no `NotImplemented` only in abstract SessionStore methods; no deviations from [RULES](../../RULES.md) or plan. After code: `code_mapper -r src`; `mypy src`, `flake8 src tests`, `black src tests` (fix all).

## Comparative analysis vs existing code

| Aspect | Existing | To change | To add |
|--------|----------|-----------|--------|
| Session | None; chat is stateless per request | — | Session entity: id, model, allowed_commands, forbidden_commands, created_at |
| Persistence | None | — | SessionStore interface; at least one impl (e.g. SQLite, Redis, or in-memory for tests) |
| Config | `config.py` has no session store settings | — | Config for store type and connection (used by step 13 and runtime) |
| **Config generator / validator** | — | — | When adding session store config: update generator overlay and `validate_project_config` per main plan §6.4 (adapter first, project on top). |

## Dependencies

- None for entity and interface. Step 06, 10, 13 depend on SessionStore.

## Deliverable

- Session dataclass or class; SessionStore abstract class and one implementation. Unit tests with in-memory or test DB.
