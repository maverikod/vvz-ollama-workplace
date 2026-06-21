# Redis / database server high-level API — analysis and recommendations

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com  

AI-generated report. Describes current state of Redis-domain components and recommended high-level methods for the database server and the corresponding client.

---

## 1. Current components

| Component | Location | Role |
|-----------|----------|------|
| **database_server** | `src/database_server/` | MCP adapter exposing Redis-domain API (sessions, messages). Runs inside container when `server_id == "database-server"`. |
| **redis_adapter** | `redis_adapter/` | Container/subproject that runs the same adapter code (database_server commands) for “Redis + adapter” deployment. |
| **database_client** | `src/database_client/` | Config only: validate, generate, CLI (generate/validate/show-schema/test-connection). No runtime client that calls session/message commands. |
| **redis_provider_client** | `redis_provider_client/` | Placeholder; no implementation yet. |

---

## 2. Existing database_server commands

| Command | Purpose |
|---------|---------|
| **session_create** | Create session; optional id, model, allowed_commands, forbidden_commands, standards, session_rules, created_at, minimize_context. Returns `{ session }`. |
| **session_get** | Get session by `session_id` (optional key_prefix). Returns `{ session }` or `{ session: null }`. |
| **session_update** | Partial update by session_id. Error if not found. |
| **message_write** | Write one message (uuid, created_at, source, body, session_id). Key: `{message_key_prefix}:{uuid}`. |
| **messages_get_by_session** | All messages for session_id, ordered by created_at. Returns `{ messages }`. |

Data model: sessions as hashes at `{session_key_prefix}:{id}`; messages as hashes at `{message_key_prefix}:{uuid}`. No index for “list sessions”; messages are found by SCAN + filter on session_id.

---

## 3. Gaps

### 3.1 Server (database_server / redis_adapter)

- **List sessions:** No command to return a list of sessions (by prefix or with limit/offset). Only session_get(session_id) exists.
- **Session + messages in one call:** No `session_get_with_messages`; caller must call session_get and messages_get_by_session separately.
- **Deletion:** No session_delete or messages_delete_by_session.

### 3.2 Client (database_client / redis_provider_client)

- No runtime API: database_client does not invoke session_* or message_* commands; redis_provider_client is empty.
- Workstation currently uses direct Redis (RedisSessionStore, RedisMessageStore, MessageStreamWriter) instead of database_server.

---

## 4. Recommended high-level methods

### 4.1 Server (database_server) — new commands

| Command | Purpose |
|---------|---------|
| **sessions_list** | List sessions: optional key_prefix, limit, offset. Returns list of session summaries (id, model, created_at). Implemented via SCAN session:* and HGET for minimal fields. |
| **session_get_with_messages** | One call returning session + messages. Params: session_id, optional key_prefix, optional message_limit (for messages). Returns `{ session, messages }`. |
| **session_delete** | Delete session by session_id (DEL key). Optional key_prefix. |
| **messages_delete_by_session** | Delete all messages for a session_id. SCAN message:* and filter by session_id; DEL each key. |

### 4.2 Client (database_client) — runtime client

Introduce a **high-level client** (e.g. `DatabaseSessionClient`) that takes an injectable async executor and exposes:

| Method | Maps to / behaviour |
|--------|----------------------|
| **get_session(session_id)** | session_get → session or None |
| **create_session(\*\*attrs)** | session_create → session |
| **update_session(session_id, \*\*attrs)** | session_update → session |
| **list_sessions(limit, offset, key_prefix)** | sessions_list → list of summaries |
| **get_messages(session_id)** | messages_get_by_session → list of messages |
| **write_message(uuid, created_at, source, body, session_id)** | message_write |
| **get_session_with_messages(session_id, message_limit)** | session_get_with_messages → { session, messages } |
| **delete_session(session_id)** | session_delete |
| **delete_messages_by_session(session_id)** | messages_delete_by_session |

Executor contract: `async (command: str, params: dict) -> dict` returning the result “data” dict, or raising on error. The workstation (or model_workspace) injects a wrapper around `proxy.call_server("database-server", command, params)` so transport stays outside database_client.

---

## 5. Implementation order

1. **Server:** Add commands sessions_list, session_get_with_messages, session_delete, messages_delete_by_session in database_server; register in `commands/__init__.py`.
2. **Client:** Add DatabaseSessionClient (or similar) in database_client with the methods above and an injectable executor; keep config validation/generation as is.
3. **Integration:** Optionally switch workstation session/message stores to use DatabaseSessionClient when database-server is configured, so one code path uses the same high-level API as other consumers.

---

## 6. References

- **Normative ТЗ (high-level DB API and client on adapter+WebSocket):** [redis_adapter/docs/SPEC_HIGH_LEVEL_DATABASE_API.md](../../redis_adapter/docs/SPEC_HIGH_LEVEL_DATABASE_API.md)
- database_server commands: `src/database_server/commands/`
- redis_facade: `src/database_server/redis_facade.py` (get_redis_client, get_storage_prefixes)
- Provider client standard: `docs/standards/provider_client_standard.md`
- Config standard: `docs/standards/provider_client_config_standard.md`
