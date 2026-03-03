<!--
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
-->

# Database-Server Command Catalog (Redis API Surface)

Reference for [step_11_database_server_full_surface.md](step_11_database_server_full_surface.md).  
Server ID: `database-server`. All parameters and results use **strict JSON Schema** (no `additionalProperties` unless documented).

## Scope

Commands cover the **Redis domain API used in production** by the workstation: message stream (write, list by session), session store (get, create, update). No direct workstation → Redis; model uses only MCP tool calls to database-server.

## Commands

### 1. `message_write`

Write one message record to storage. Key layout: `{message_key_prefix}:{uuid}`; value = hash (uuid, created_at, source, body, session_id).

| Parameter     | Type   | Required | Description |
|---------------|--------|----------|-------------|
| uuid          | string | yes      | Message UUID (primary key). |
| created_at   | string | yes      | ISO 8601 timestamp. |
| source       | string | yes      | One of: user, model, tool, external_agent. |
| body         | string | yes      | Message content. |
| session_id   | string | yes      | Session UUID. |

**Result:** `{"written": true, "key": "message:<uuid>"}` or error.

**JSON Schema (params):** `type: "object"`, `properties` as above, `required: ["uuid","created_at","source","body","session_id"]`, `additionalProperties: false`.

---

### 2. `messages_get_by_session`

Return all messages for a session, ordered by created_at. Uses scan by key prefix and filters by session_id.

| Parameter     | Type   | Required | Description |
|---------------|--------|----------|-------------|
| session_id   | string | yes      | Session UUID. |
| key_prefix   | string | no       | Key prefix (default: "message"). |

**Result:** `{"messages": [ {"uuid","created_at","source","body","session_id"}, ... ]}`.

**JSON Schema (params):** `type: "object"`, `properties`: session_id (string), key_prefix (string, default "message"); `required: ["session_id"]`, `additionalProperties: false`.

---

### 3. `session_get`

Return session by id or null if not found.

| Parameter     | Type   | Required | Description |
|---------------|--------|----------|-------------|
| session_id   | string | yes      | Session UUID. |
| key_prefix   | string | no       | Key prefix (default: "session"). |

**Result:** `{"session": { "id", "model", "allowed_commands", "forbidden_commands", "standards", "session_rules", "created_at", "minimize_context" } }` or `{"session": null}`.

**JSON Schema (params):** `type: "object"`, `properties`: session_id (string), key_prefix (string, default "session"); `required: ["session_id"]`, `additionalProperties: false`.

---

### 4. `session_create`

Create a new session and persist. Id generated if not provided in attrs.

| Parameter     | Type   | Required | Description |
|---------------|--------|----------|-------------|
| model        | string | no       | Model name. |
| allowed_commands  | array of string | no | Allowed command names. |
| forbidden_commands| array of string | no | Forbidden command names. |
| standards    | array of string | no | Standards list. |
| session_rules| array of string | no | Session rules. |
| created_at   | string | no       | ISO 8601. |
| id           | string | no       | Session id (optional; generated if omitted). |
| minimize_context | boolean | no    | Minimize context flag. |

**Result:** `{"session": { "id", "model", ... } }`.

**JSON Schema (params):** `type: "object"`, `properties` as above with types, `required: []`, `additionalProperties: false`.

---

### 5. `session_update`

Update existing session by id. Returns error if session not found.

| Parameter     | Type   | Required | Description |
|---------------|--------|----------|-------------|
| session_id   | string | yes      | Session UUID. |
| model        | string | no       | New model (partial update). |
| allowed_commands  | array of string | no | New allowed list. |
| forbidden_commands| array of string | no | New forbidden list. |
| standards    | array of string | no | New standards. |
| session_rules| array of string | no | New session_rules. |
| minimize_context | boolean | no    | New flag. |
| key_prefix   | string | no       | Key prefix (default: "session"). |

**Result:** `{"session": { "id", "model", ... } }`.

**JSON Schema (params):** `type: "object"`, `properties` as above, `required: ["session_id"]`, `additionalProperties: false`.

---

### 6. `health`

Adapter health check (optional; may be provided by mcp-proxy-adapter built-in). If implemented by database-server: returns storage connectivity (e.g. Redis PING). Parameters: none. Result: `{"status": "ok"}` or error.

---

## Tool-level auth/TLS

Aligned with proxy mTLS policy: database-server uses mTLS (transport.verify_client); client calls via proxy with same policy.

## Verification

- `list_servers` / `help` (via proxy) shows database-server and the above commands with strict JSON Schema.
- `call_server(server_id="database-server", command="message_write", params={...})` (and other key commands) succeed with real Redis backend when configured.
