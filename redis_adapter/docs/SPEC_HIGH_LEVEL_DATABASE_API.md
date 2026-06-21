# High-level database API — technical specification (ТЗ)

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

Technical specification for **project-specific high-level database access**: domain API (sessions and messages) on the server side and a **client on adapter + WebSocket** that exposes this API to the model workspace and other consumers. Context: root [docs/plans/refactoring_adapter_structure/SPEC.md](../../docs/plans/refactoring_adapter_structure/SPEC.md), [docs/SUBPROJECTS_OVERVIEW.md](../../docs/SUBPROJECTS_OVERVIEW.md). Analysis: [docs/reports/redis_database_high_level_api_analysis.md](../../docs/reports/redis_database_high_level_api_analysis.md).

---

## 1. Purpose and scope

- **Server:** The **database_server** (run in the redis-adapter context with `server_id` "database-server") exposes a **domain API**: sessions and messages, not raw Redis commands. This API is the high-level contract for storage used by the model workspace (and any other consumer).
- **Client:** A **high-level database client** connects to the adapter (via proxy) over **WebSocket** (same transport as other adapter clients), calls the database_server commands, and exposes **project-specific methods** (get_session, create_session, list_sessions, get_session_with_messages, etc.) so that callers do not deal with command names and parameters directly.
- **Transport:** Client ↔ server interaction uses the **adapter client** from mcp-proxy-adapter: WebSocket (wss:// via proxy) with JSON-RPC; same contract as ollama_provider_client and redis_provider_client (see [docs/standards/provider_client_standard.md](../../docs/standards/provider_client_standard.md) for the general client pattern).

---

## 2. Server: high-level commands

The following commands form the **high-level database API**. Implementation lives in **database_server** (root `src/database_server/`); the server is deployed in the **redis-adapter** container when registered as **database-server**.

### 2.1 Existing commands (current)

| Command | Purpose |
|--------|---------|
| **session_create** | Create a session; optional id, model, allowed_commands, forbidden_commands, standards, session_rules, created_at, minimize_context. Returns `{ session }`. |
| **session_get** | Get session by session_id (optional key_prefix). Returns `{ session }` or `{ session: null }`. |
| **session_update** | Partial update by session_id. Error if not found. |
| **message_write** | Write one message (uuid, created_at, source, body, session_id). Returns `{ written, key }`. |
| **messages_get_by_session** | All messages for session_id, ordered by created_at. Returns `{ messages }`. |

### 2.2 New commands (to be implemented)

| Command | Purpose |
|--------|---------|
| **sessions_list** | List sessions: optional key_prefix, limit, offset. Returns list of session summaries (e.g. id, model, created_at). Implementation: SCAN session:* and HGET minimal fields. |
| **session_get_with_messages** | Single call returning session + messages. Params: session_id, optional key_prefix, optional message_limit. Returns `{ session, messages }`. |
| **session_delete** | Delete session by session_id (DEL key). Optional key_prefix. |
| **messages_delete_by_session** | Delete all messages for session_id. SCAN message:* and filter by session_id; DEL each key. |

### 2.3 Data model (Redis)

- **Sessions:** Key `{session_key_prefix}:{session_id}`; type hash; fields: model, allowed_commands, forbidden_commands, standards, session_rules, created_at, minimize_context (arrays as JSON).
- **Messages:** Key `{message_key_prefix}:{uuid}`; type hash; fields: uuid, created_at, source, body, session_id`.
- Index for “list sessions” is implicit (SCAN by session prefix). Messages are found by SCAN message:* and filter by session_id.

---

## 3. Client: high-level API on adapter + WebSocket

### 3.1 Transport and base

- **Base:** The client is **based on the adapter client** (mcp-proxy-adapter JsonRpcClient or equivalent): connection to the proxy/adapter over **WebSocket** (wss:// when TLS), same request/response protocol as other provider clients.
- **Target server:** All high-level methods map to **database-server** commands (server_id `"database-server"`). The client uses the adapter’s `call_server(server_id, command, params)` (or equivalent) under the hood; no direct Redis access.

### 3.2 Contract

- **Configuration:** Client is configured with adapter/proxy URL (e.g. database_server or proxy URL), TLS/certs, timeouts — consistent with [database_client config](../../src/database_client/) and root docs.
- **Errors:** All failures (network, timeout, adapter error, command error) are mapped to a small set of client-side exceptions (e.g. TransportError, TimeoutError, ValidationError, NotFoundError) so that callers do not depend on adapter-specific codes.

### 3.3 High-level methods (project-specific)

The client exposes the following **project-specific** methods. Each maps to one or more database_server commands.

| Method | Server command(s) | Returns |
|--------|-------------------|--------|
| **get_session(session_id)** | session_get | Session dict or None |
| **create_session(\*\*attrs)** | session_create | Session dict |
| **update_session(session_id, \*\*attrs)** | session_update | Session dict |
| **list_sessions(limit, offset, key_prefix)** | sessions_list | List of session summaries |
| **get_messages(session_id)** | messages_get_by_session | List of message dicts |
| **write_message(uuid, created_at, source, body, session_id)** | message_write | Result (e.g. written, key) |
| **get_session_with_messages(session_id, message_limit)** | session_get_with_messages | `{ session, messages }` |
| **delete_session(session_id)** | session_delete | Success / void |
| **delete_messages_by_session(session_id)** | messages_delete_by_session | Success / void |

- **Async:** All methods are **async** and use the adapter client’s async API (WebSocket send/receive).
- **Validation:** Required parameters (e.g. session_id, uuid, source, body) are validated on the client before calling the server; optional parameters (key_prefix, limit, offset, message_limit) have documented defaults.

### 3.4 Placement of the client

- **Package:** The high-level client is implemented in the **database_client** package (root `src/database_client/`), which already provides config validation and generation. The runtime client class (e.g. `DatabaseSessionClient` or `HighLevelDatabaseClient`) is added there and uses an injectable adapter-client callable (or builds the adapter client from config) so that transport remains “adapter + WebSocket” and the model workspace does not depend on raw command names.
- **Alternative:** If the project chooses to keep “storage client” only in **redis_provider_client**, the same high-level methods can be implemented there, again **on top of the adapter client** (WebSocket to the adapter that serves database-server). The spec does not mandate the package name, only the transport (adapter + WebSocket) and the method list above.

---

## 4. Implementation order

1. **Server:** Implement in database_server the new commands: sessions_list, session_get_with_messages, session_delete, messages_delete_by_session; register them in the adapter command registry.
2. **Client:** Implement the high-level client class (adapter + WebSocket), with the methods from §3.3 and error mapping; integrate with existing database_client config (or redis_provider_client if chosen).
3. **Integration:** Optionally switch model workspace (or Agent Workstation) session/message stores to use this client when database-server is configured, so that all consumers use the same high-level API.

---

## 5. References

- Main Redis adapter ТЗ (raw Redis API): [ТЗ.md](ТЗ.md)
- Database server commands (current): root `src/database_server/commands/`
- Redis facade: root `src/database_server/redis_facade.py`
- Adapter client (WebSocket): mcp-proxy-adapter JsonRpcClient; root `src/ollama_workstation/proxy_client.py` (pattern)
- Analysis report: [docs/reports/redis_database_high_level_api_analysis.md](../../docs/reports/redis_database_high_level_api_analysis.md)
