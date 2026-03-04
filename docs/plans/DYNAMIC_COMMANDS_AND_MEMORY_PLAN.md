# Dynamic commands and Redis memory — plan

**Author:** Vasiliy Zdanovskiy  
**Email:** [vasilyvz@gmail.com](mailto:vasilyvz@gmail.com)  

This document specifies: (1) a dynamically updatable list of tools/commands for the model, built from proxy servers and their schemas, with allow/deny policy and safe names/aliases per model; (2) a **context representation layer** for multiple providers (Anthropic, Opera AI, OLLAMA, etc.) with preservation of context on model change; (3) message-stream persistence in Redis inside the container.

**Step-by-step implementation plan** (1 step = 1 file) and **interaction diagrams** are in the subdirectory **[docs/plans/dynamic_commands_memory/](dynamic_commands_memory/)**. See `README.md` there for the step index and `00_objects_and_diagrams.md` for the object scheme and Mermaid diagrams. Step files reference this plan (e.g. §3.5 Schema and structure of data stores, §4.2a–4.2b vector table and search) and are kept in sync with it.

---

## Object model (by-object scheme)

Objects and their responsibilities. Naming is conceptual; implementation may split or merge classes per project conventions (one class per file, max 350–400 lines).


| Domain                      | Object                                                           | Responsibility                                                                                                                                                                                                                                                                                                                                                               |
| --------------------------- | ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Commands**                | `CommandsPolicyConfig`                                           | allowed_commands, forbidden_commands, commands_policy (allow_by_default / deny_by_default). Loaded from config.                                                                                                                                                                                                                                                              |
|                             | `CommandId`                                                      | Canonical id: command_name + server_id (e.g. `ollama_chat.ollama-adapter`). Value object.                                                                                                                                                                                                                                                                                    |
|                             | `SafeNameTranslator`                                             | Canonical id → model-safe name (dot/space/hyphen → underscore; `[a-zA-Z0-9_]` only).                                                                                                                                                                                                                                                                                         |
|                             | `ToolCallRegistry`                                               | Per-request or per-session: display_name → (command_name, server_id) for resolving model tool calls. Built when building effective tool list.                                                                                                                                                                                                                                |
|                             | `CommandSchema`                                                  | name, description, parameters (JSON Schema). From proxy help/schema.                                                                                                                                                                                                                                                                                                         |
|                             | `CommandDiscovery`                                               | Fetches list_servers, per-server schemas; builds flat list of CommandId + CommandSchema. Update: startup + periodic (config `command_discovery_interval_sec`); mark commands unavailable when server unreachable.                                                                                                                                                            |
|                             | `CommandAliasRegistry`                                           | command_id × model (or representation_type) → display_name. Config or DB. Used when building tool list for session.                                                                                                                                                                                                                                                          |
|                             | `EffectiveToolListBuilder`                                       | Merge config policy + config lists + session allowed/forbidden → effective list; for each command resolve alias or safe name; build ToolCallRegistry; produce list for representation layer.                                                                                                                                                                                 |
| **Session**                 | `Session`                                                        | id (UUID4), model, allowed_commands, forbidden_commands, created_at, etc. Entity.                                                                                                                                                                                                                                                                                            |
|                             | `SessionStore`                                                   | Persistence: get(session_id), create(attrs), update(session). Interface; impl e.g. SQLite, PostgreSQL, Redis.                                                                                                                                                                                                                                                                |
|                             | `SessionInitCommand`                                             | Adapter command: JSON request (command name, **parameters** = session record fields); creates session, returns session_id (§4.1).                                                                                                                                                                                                                                            |
|                             | `SessionUpdateCommand`                                           | Adapter command: session_id, optional model, allowed_commands, forbidden_commands; sets or changes session model and lists.                                                                                                                                                                                                                                                  |
|                             | `AddCommandToSessionCommand` / `RemoveCommandFromSessionCommand` | Add/remove command id to/from session lists; reject and log if adding config-forbidden.                                                                                                                                                                                                                                                                                      |
| **Context representation**  | `ContextRepresentation` (base)                                   | Abstract: serialize_tools(tool_list), serialize_messages(messages), optional max_context_tokens().                                                                                                                                                                                                                                                                           |
|                             | `OllamaRepresentation`, `GoogleRepresentation` (Gemini), …       | Per-provider serialization; see §2.5 for Ollama and Google (context size + representation).                                                                                                                                                                                                                                                                                  |
|                             | `RepresentationRegistry`                                         | model_id (or family) → ContextRepresentation type/instance. Used when building request for session.                                                                                                                                                                                                                                                                          |
| **Memory**                  | `MessageSource`                                                  | Enum: user, model, tool, external_agent.                                                                                                                                                                                                                                                                                                                                     |
|                             | `RedisMessageRecord`                                             | uuid (primary key), created_at, source, body, session_id. Aligned with chunk_metadata_adapter (SemanticChunk); by uuid the full message can be assembled.                                                                                                                                                                                                                    |
|                             | `MessageStreamWriter`                                            | Writes RedisMessageRecord to Redis (LIST or STREAM). Called from chat flow.                                                                                                                                                                                                                                                                                                  |
| **Memory / index**          | `MemoryIndexWorker`                                              | Reads unprocessed messages from Redis; calls **chunker** (e.g. svo_client) only — chunker **chunks and vectorizes** (it calls the vectorizer internally); writes vector table, updates vector index and BM25 store; marks processed. See §4.2a. **Embed/vectorizer client** (e.g. embed_client) is used **at query time** to obtain **query embedding** for semantic search. |
|                             | Vector table (DB)                                                | chunk_id (UUID4, PK), vector, vector_index_id (integer; from FAISS add). **is_deleted** (soft delete); all queries exclude deleted. Add: write vector to DB → add to FAISS → store returned ID. Reindex: build FAISS only from non-deleted rows; then deleted vectors are gone from index.                                                                                   |
|                             | Vector index (e.g. FAISS)                                        | Add returns integer ID; we do **not** remove vectors on delete. Deleted chunks excluded at query time (filter by is_deleted in DB before sort/return). Reindex rebuilds from non-deleted rows only.                                                                                                                                                                          |
|                             | BM25 / chunk store                                               | chunk_id + tokens (and optional message_id); exclude deleted (filter by vector table or shared deleted set); body/session_id resolved by lookup (e.g. Redis Lua).                                                                                                                                                                                                            |
|                             | `SemanticMemorySearch` (interface)                               | search_semantic(query_embedding, session_id, top_k) → list of (chunk_id, message_id, score, text); search_bm25(query_tokens, session_id, top_k) → same shape. Resolution of body/session_id from chunk_id via lookup (e.g. Redis Lua). Used by RelevanceSlotBuilder.                                                                                                         |
| **Context window**          | `ContextBuilder`                                                 | Load session → model → effective limit; load messages; apply order (standards, rules, N messages, relevance slot); trim; fill slots; produce payload for representation.                                                                                                                                                                                                     |
|                             | `TrimmedContext`                                                 | Result: ordered segments (standards, session_rules, last_n_messages, relevance_slot). Token counts / sizes.                                                                                                                                                                                                                                                                  |
|                             | `RelevanceSlotBuilder`                                           | Unified: rank session chunks + doc chunks by vector distance to current message; take by increasing distance. Or fixed order: semantic then doc.                                                                                                                                                                                                                             |
|                             | `DocumentationSource` (interface)                                | list_items(session_id?) → TOC; get_content(item_id) → text. Pluggable backend.                                                                                                                                                                                                                                                                                               |
|                             | `DocumentationSlotBuilder`                                       | Fills doc slot: canon first, then clarifications; uses DocumentationSource.                                                                                                                                                                                                                                                                                                  |
| **External data / context** | `Database`                                                       | External data source for the documentation part of context. Capabilities: semantic search, full-text search, filter-by-pattern (see chunk_metadata_adapter). Access: write, read (one or set of records), search. Each instance has a **capability metric** (what it supports). Result count and relevance limits.                                                           |
|                             | `DatabaseManager`                                                | Add database, remove database, get database(s) by query (filter by properties/capabilities). Used to register external sources and resolve which databases to query for context.                                                                                                                                                                                             |
| **Tools → model**           | `CallStack`                                                      | Stack of (tool_name, depth) or (call_id, depth). Push on entering model call from tool, pop on return.                                                                                                                                                                                                                                                                       |
|                             | `ModelCallDepthGuard`                                            | Before invoking model from tool: check current_depth < max_model_call_depth; else return error. Uses CallStack.                                                                                                                                                                                                                                                              |
|                             | `ModelCallingToolAllowList`                                      | Config or fixed set of command_ids that may trigger model invocation.                                                                                                                                                                                                                                                                                                        |


---

## 1. Dynamic command list

### 1.1 Goal

- Obtain the list of servers from the proxy.
- Poll each server’s schema (commands and metadata); all servers use the adapter, so their IDs and command definitions can be retrieved by polling.
- Build a single flat list of commands for the model. Each command is identified as **Command.ServerId** (e.g. `ollama_chat.ollama-adapter`, `chunk.svo-chunker`).
- The model sees one unified list of commands with descriptions and parameters; execution is still via proxy (e.g. `call_server` under the hood or a single “execute command” tool that accepts `command_id` and params).

### 1.2 Update strategy (dynamic)

The command list is **updated dynamically**:

- **On startup** — fetch the list from the proxy when the adapter (or workstation component) starts.
- **Periodically** — refresh from the same proxy on a schedule. Add a **config setting for the check interval** (e.g. `command_discovery_interval_sec` or `command_discovery_refresh_interval_sec`) so that periodic checks run at the configured frequency.
- **Unavailable server:** When a server is unreachable (e.g. health check or schema fetch fails), **mark the command(s) of that server as unavailable** (e.g. flag or separate "available" set). Such commands are not offered to the model until the server is reachable again (next successful refresh). Do not remove them from the discovered list; only mark availability.

### 1.3 Data flow

1. Call proxy **list_servers** (existing) → get `server_id`, `server_url`, `commands` (if proxy already returns command list per server, use it; otherwise proceed to step 2).
2. For each server, obtain command schemas (e.g. via proxy **help** for that server, or a dedicated “schema”/“openapi” endpoint if available). From adapter-based servers we can get command names, summaries, parameters (JSON Schema).
3. For each command, form **command_id** = `CommandName.ServerId` (e.g. `echo.ollama-adapter`, `chunk.svo-chunker`).
4. Build OLLAMA-format tool definitions: `name` = command_id or a normalized form, `description` = server name + command summary, `parameters` = merged/namespaced schema so the model sees one list of tools.
5. Apply **allow/deny policy** (see 1.4) and expose only the resulting set to the model.

### 1.4 Config: allowed / forbidden commands and policy

Add to config (e.g. workstation YAML or adapter config section):

- **command_discovery_interval_sec** — (optional) interval in seconds for periodic refresh of the command list from the proxy. If 0 or omitted, only on-startup discovery is used; if set to a positive value, a background task refreshes the list at this interval. When a server is unreachable, its commands are marked unavailable (see §1.2).
- **allowed_commands** — list of command identifiers (e.g. `ollama_chat.ollama-adapter`, `chunk.svo-chunker`). Optional; meaning depends on policy.
- **forbidden_commands** — list of command identifiers. **Takes precedence over allowed**: if a command is in forbidden, it is never exposed regardless of allowed.
- **commands_policy** — one of:
  - **allow_by_default** — expose all commands from the discovered list except those in `forbidden_commands`. If `allowed_commands` is non-empty, use it as an **additional filter** (intersection): only commands that are both discovered and in `allowed_commands` pass, minus `forbidden_commands`. If `allowed_commands` is empty, expose all discovered minus forbidden.
  - **deny_by_default** — expose only commands that are in `allowed_commands`, minus any that are also in `forbidden_commands`.

So: **forbidden_commands** overrides **allowed_commands**; **commands_policy** defines whether the default is “all visible” or “none visible unless allowed”.

### 1.5 Safe command name translation and registry

- **Problem:** Command identifiers like `Command.ServerId` (e.g. `ollama_chat.ollama-adapter`, `chunk.svo-chunker`) can contain characters (dot, hyphen, space) that are unsafe or invalid for some model APIs (OpenAI, Anthropic, Ollama, etc.). Names must be safe across providers.
- **Translation rule:** Produce a **model-safe name** from the canonical identifier:
  - Replace **dot (.)**, **space**, **hyphen (-)** with **underscore (_)**.
  - Allow only `[a-zA-Z0-9_]` in the final name; replace or drop any other character.
  - Optionally collapse consecutive underscores to one; optionally enforce a max length if a provider has a limit.
- **Examples:** `ollama_chat.ollama-adapter` → `ollama_chat_ollama_adapter`; `chunk.svo-chunker` → `chunk_svo_chunker`.
- **Reverse lookup:** Translation is one-way (safe name does not uniquely decode back to command + server_id). Maintain a **registry**: when building the tool list for a session, for each (command_name, server_id) compute the safe name and store **safe_name → (command_name, server_id)**. When the model invokes a tool by safe name, resolve via this registry to execute the correct command on the correct server.
- **Scope:** Registry is per session or per request (built when building the effective tool list for that session); it is the source of truth for resolving tool calls from the model.

### 1.6 Command registry and aliases per model

- **Goal:** Command names should not cause problems when used with different models (reserved words, format constraints, provider quirks). Since command names are not known in advance, support **aliases per model** (or per model type / provider).
- **Command registry:** A **registry of commands** stores, for each logical command (e.g. identified by command_name + server_id or by canonical id):
  - **Aliases per model (or per representation type):** mapping from model id (or representation type id) to the **name** to expose to that model. Example: for `ollama_chat.ollama-adapter`, model A might see `ollama_chat_ollama_adapter`, model B might see `tool_ollama_chat` (if that model prefers a prefix).
- **Usage:** When building the tool list for a session, the session has a **model**. For each command in the effective list, look up the alias for that model (or for the representation type of that model); if present, use it as the tool name sent to the model; otherwise fall back to the **safe name** from §1.5. The registry used for **reverse lookup** (model’s tool call → command + server_id) must map the **actual name sent to the model** (alias or safe name) → (command_name, server_id).
- **Config/storage:** Aliases can be configured in config (e.g. YAML per model) or in a DB table (command_id, model_or_type, display_name). Default: use safe name when no alias is defined.

### 1.8 Session store (database)

- **Sessions** are stored in a **database** (e.g. SQLite, PostgreSQL, or Redis-backed store). **The session must describe the model** — it must include which model is used for that session. Stored attributes at least:
  - **id** — session identifier (UUID4).
  - **model** — model name or id used for this session (e.g. `llama3.2`, `qwen3`). **Context window size is determined by this model** (see §4.4): effective limit = min(model window, config max_context_tokens). We choose the smaller value (config caps resource usage).
  - **allowed_commands** — list of command identifiers allowed for this session (optional; empty or null = use policy default).
  - **forbidden_commands** — list of command identifiers forbidden for this session (optional).
  - **Standards and session rules** — passed as **arguments at session create** (optional). Stored in **local Redis** (e.g. keys by session_id); **can be updated** later (e.g. via session update or dedicated update). Schema and DB design must account for this (see §3.5.2 and §4.3).
  - Other attributes as needed (e.g. created_at, user_id, metadata, external DB list for session).
- **Policy** is **not** stored per session: it is taken from **config** (`commands_policy`: allow_by_default | deny_by_default). Session lists only refine the set (see §1.9).
- Session record is created when the session-init command is called (and returns session_id). The **model** can be set at session start (e.g. passed as parameter to session-init) or updated later; it is used for all context building for that session.

### 1.9 Per-session commands: add / remove; priority of config over session

- **Commands to manage session tools:**
  - **Add command to session** — add a command identifier to the session’s allowed list (or remove from session’s forbidden list). If the command is in **config** `forbidden_commands`, **do not add** and **log an error** (e.g. "command X is forbidden by config and cannot be added to session"). Session store is not updated for that command.
  - **Remove command from session** — remove the command from the session’s allowed list or add it to the session’s forbidden list so it is no longer available in that session.
- **Priority:** Config lists have **higher** priority than session lists. Session lists **cannot** override config.
  - **Config `forbidden_commands`** — if a command is here, it is **never** available, regardless of session allowed/forbidden.
  - **Config `allowed_commands`** and **config `commands_policy`** — define the base candidate set (deny_by_default ⇒ only config allowed; allow_by_default ⇒ all discovered minus config forbidden).
  - **Session `forbidden_commands`** — can only **further restrict** (exclude more commands for this session).
  - **Session `allowed_commands`** — when set, restricts the session to a **subset** of the config-derived candidates (session cannot allow what config forbids or, under deny_by_default, what config did not allow).
- **Effective tool list** for a request = merge(config, session): apply config policy and config lists first, then apply session allowed/forbidden; result is the list of tools exposed to the model for that session.

### 1.10 Summary (commands)

- Single flat list of commands for the model, IDs like `Command.ServerId`.
- List is built from proxy server list + per-server command schemas (polling).
- **Safe names:** Translate identifiers to model-safe names (dot/space/hyphen → underscore; only `[a-zA-Z0-9_]`). Registry **safe_name → (command, server_id)** for resolving tool calls from the model.
- **Command registry and aliases:** Registry of commands with **aliases per model** (or per representation type); if an alias is defined for the session’s model, use it as the tool name; otherwise use safe name. Reverse lookup must support the actual name sent to the model.
- Config: `allowed_commands`, `forbidden_commands`, `commands_policy` (allow_by_default | deny_by_default). **Policy is always from config.**
- **Session store** (DB): session id, **model** (required — the session must describe the model; context size is derived from it), allowed_commands, forbidden_commands, other attributes. **Session lists have lower priority than config**; config forbidden can never be overridden by session.
- **Commands:** add command to session, remove command from session. Adding a config-forbidden command is rejected and logged.
- **Update strategy:** Dynamic — on startup + periodic (config `command_discovery_interval_sec`); mark commands unavailable when server unreachable (§1.2).

---

## 2. Context representation layer (universal representation for multiple providers)

### 2.1 Goal

- Support **multiple providers** (Anthropic, Opera AI, open-source such as OLLAMA, etc.). Each provider (or model) expects tools and messages in a specific format (e.g. OpenAI-style tools, Anthropic tool use, OLLAMA function format).
- **Separate the tool layer from their representation:** tools are defined once (canonical list, schemas, safe names / aliases); **representation** is how they are serialized for a given model API (format of the tools array, message shape, schema style).
- When the **session model is set or changed**, **context (conversation history) is preserved**; it is **trimmed** only as needed to fit the new model’s context window. The **representation** is **swapped** to the one appropriate for the new model — same tools and same history, different serialization.

### 2.2 Base class and representation types

- **Base class** for context/tool representation with **virtual methods**, e.g.:
  - Serialize tool list for the model (name, description, parameters in the provider’s format).
  - Serialize message list (user/assistant/tool messages) in the provider’s format.
  - Optional: max context size for the model, token counting, or other provider-specific behaviour.
- **Derived classes** implement one representation type per provider (or per API style): e.g. `OpenAIRepresentation`, `AnthropicRepresentation`, `OllamaRepresentation`, `OperaAIRepresentation`. Each implements the same interface so the rest of the system does not depend on the provider.
- **Registry of representation types and allowed models:** mapping from **model id** (or model family / provider name) to **representation type** (the class or type id). When building a request for a session, the session’s **model** is used to select the representation type; that type is used to serialize tools and messages for the API call.

### 2.3 Session model change and context preservation

- **Per session:** The user can **set the model** at session start or **change it** later (e.g. via session-update or a dedicated parameter).
- **On model change:**
  - **Context (message history) is preserved** — no reset of the conversation.
  - **Trimming:** If the new model’s context window is smaller, the history is **trimmed** according to the same rules (e.g. last N messages, or by tokens, within the new model’s limit). Standards and session rules are reapplied; relevance slot and documentation slot are refilled within the new size.
  - **Representation:** The **representation type** for the new model is looked up in the registry; from then on, tools and messages are serialized using that representation until the model is changed again.
- This allows switching between e.g. OLLAMA and a cloud provider within the same session without losing the dialogue; only the format and size limit change.

### 2.4 Summary (context representation)

- **Separation:** Tools (canonical) vs. representation (per-provider serialization). Base class with virtual methods; derived classes per provider.
- **Registry:** Model id (or family) → representation type. Used when building requests for a session.
- **Session model change:** Context preserved; trim to new model’s window if needed; representation swapped to match the new model.

### 2.5 Per-model scheme: context size and representation (Ollama and Google)

For each supported provider we define: (1) **how the model is identified** (model_id and registry mapping), (2) **how context size (context window) is determined**, (3) **how context representation works** (tools format, message format, and any provider-specific rules). Below only **Ollama** and **Google** (Gemini) are specified in detail; other providers (OpenAI, Anthropic, Opera AI) follow the same pattern and are added when needed.

---

#### 2.5.1 Ollama

- **Model identification:** Model id is the name used in the session (e.g. `llama3.2`, `qwen3`, `mistral`). The registry maps **Ollama models** to `OllamaRepresentation`. Mapping can be: (a) **by prefix** — e.g. no prefix means local OLLAMA, or configurable prefix like `ollama:`; (b) **by explicit list** in config (e.g. `ollama_models: [ "llama3.2", "qwen3", ... ]`); (c) **by default** — if the model is not in any other provider’s list, treat as Ollama. Recommendation: config list of model ids that use Ollama representation, or “all models not matched by another provider”.
- **Context size (context window):** The effective context limit for Ollama is determined by one of: (1) **OLLAMA API** — call `GET /api/show?name=<model>` (or equivalent) and read the model’s `parameter_size` or documented context length if the API returns it; (2) **Config map** — `model_context_windows: { "llama3.2": 128000, "qwen3": 32768, ... }` in config, keyed by model id; (3) **Default fallback** — if unknown (e.g. 4096 or 8192) so that context build does not fail. Implementation chooses one or combines (e.g. config override, then API, then default). Result: **effective_limit = min(model_context_window, config max_context_tokens)**.
- **Context representation (Ollama):**
  - **Tools:** Serialized for OLLAMA chat API (`/api/chat`). Format: array of objects with `type: "function"` and `function: { name, description, parameters }`. `parameters` is a JSON Schema object (e.g. `{ "type": "object", "properties": { ... }, "required": [ ... ] }`). Names must be model-safe (e.g. underscores only); alias or safe name from the tool list is used as `function.name`.
  - **Messages:** Array of message objects. Each message: `role` (`"user"` | `"assistant"` | `"system"`) and `content` (string). For tool use: OLLAMA supports `tool_calls` and tool results in message parts (format as per OLLAMA API doc: e.g. assistant message with `content` and optional `tool_calls`; next user/tool message with `role: "tool"` and content as tool result). Exact shape (e.g. `parts` with `type: "tool_use"` / `type: "tool_result"`) follows the current OLLAMA chat API specification.
  - **Token counting (optional):** If the representation implements `max_context_tokens(model_id)`, it can return the model’s context size for trimming; otherwise ContextBuilder uses the shared lookup (config or API) above.
- **Summary (Ollama):** Registry maps Ollama model ids → OllamaRepresentation. Context size from config map, OLLAMA API, or default. Tools = `type "function"`, function name/description/parameters; messages = role + content (+ tool_calls/tool results per OLLAMA spec).

---

#### 2.5.2 Google (Gemini)

- **Model identification:** Model id is the name used in the session (e.g. `gemini-1.5-pro`, `gemini-1.5-flash`, `gemini-2.0-flash`). The registry maps **Google/Gemini models** to `GoogleRepresentation` (or `GeminiRepresentation`). Mapping: (a) **by prefix** — e.g. `gemini-` or `google-`; (b) **by explicit list** in config (e.g. `google_models: [ "gemini-1.5-pro", ... ]`). Recommendation: match by prefix `gemini-` (and optionally `google-`) so that new Gemini variants are picked up without config change.
- **Context size (context window):** Google Gemini models have large, model-specific context windows (e.g. 1M tokens for 1.5 Pro/Flash in some variants; 2M for 2.0; see Google’s documentation). Determination: (1) **Config map** — `model_context_windows: { "gemini-1.5-pro": 1048576, "gemini-1.5-flash": 1048576, "gemini-2.0-flash": 2097152, ... }` in config; (2) **Default by family** — e.g. all `gemini-1.5-`* → 1M, `gemini-2.0-*` → 2M if not in map; (3) **Default fallback** — e.g. 32k or 128k for unknown Gemini. Result: **effective_limit = min(model_context_window, config max_context_tokens)**. Google API may also expose context length in model metadata; implementation can use that when available.
- **Context representation (Google / Gemini):**
  - **Tools:** Serialized for Google Generative AI (Gemini) API. Format: **function declarations** — array of `FunctionDeclaration` objects with `name`, `description`, and `parameters` (Google’s schema format: `type: "object"`, `properties`, etc.). Tool names must comply with Gemini constraints (e.g. alphanumeric and underscore). Use alias or safe name as `name`.
  - **Messages:** Google Chat format. Each message has `role` (`user` | `model`) and `parts`. Parts can be: `{ inlineData: ... }` for media, or `{ text: "..." }` for text, or `{ functionCall: { name, args } }` for tool call, or `{ functionResponse: { name, response } }` for tool result. Internal message list (user/assistant/tool) is mapped: user → role `user`, parts `[{ text: content }]`; assistant with tool_calls → role `model`, parts with `functionCall` entries; tool result → role `user`, parts `[{ functionResponse: { name, response } }]`. System instruction can be sent as a separate field (e.g. `systemInstruction` in the generateContent request) if the API supports it.
  - **Token counting (optional):** If implemented, use config map or Google’s documented context sizes; no standard “show model” call like OLLAMA, so config or defaults are primary.
- **Summary (Google):** Registry maps Gemini model ids (e.g. prefix `gemini-`) → GoogleRepresentation. Context size from config map or family/default. Tools = FunctionDeclaration (name, description, parameters); messages = role + parts (text, functionCall, functionResponse) per Gemini API.

---

#### 2.5.3 Registry and lookup flow

- **Context size lookup:** Given `session.model` (e.g. `llama3.2` or `gemini-1.5-pro`), ContextBuilder (or a dedicated helper) obtains the effective context window: (1) optional provider-specific API (Ollama only today); (2) config `model_context_windows[model_id]`; (3) provider-specific default (Ollama 4k–8k, Gemini 1M/2M by family); (4) global default (e.g. 4096). Then **effective_limit = min(model_window, config max_context_tokens)**.
- **Representation lookup:** Given `session.model`, RepresentationRegistry.get_representation(model_id) returns the representation instance (OllamaRepresentation or GoogleRepresentation). Registry is populated at startup from config (e.g. list of Ollama model ids, list or prefix for Google) or code. Representation is used to serialize tools and messages for the outgoing API call.

---

## 3. Memory — Redis message stream

### 3.1 Goal

- Run **Redis** inside the same container as the adapter (or in a sidecar; plan assumes “in container” for simplicity).
- Persist the **message stream** into Redis: every message that flows through the chat (user, assistant, tool, external agent) is written with metadata.
- Redis is used as **transmission and synchronization** with the permanent corporate database; the full semantic-chunk pipeline is handled by a separate project. We use only the fields we need; **field names** are aligned with **chunk_metadata_adapter** (SemanticChunk) for sync with the corporate DB.

### 3.2 Recorded fields

Field names aligned with **chunk_metadata_adapter** (SemanticChunk). We use only the subset we need. For each message write to Redis:

- **uuid** — unique identifier of the message (UUID4). **Primary key.** Same name as SemanticChunk.uuid; this value is the message id (when chunks are built, chunk.source_id = this uuid). Storage: keyed by uuid; indices (e.g. by session_id) for listing are secondary.
- **created_at** — date and time, ISO 8601 with timezone, sub-second (same as SemanticChunk.created_at).
- **source** — who produced the message (same as SemanticChunk.source): `user`, `model`, `tool`, `external_agent`.
- **body** — message content (same as SemanticChunk.body): text or JSON for tool calls/results.
- **session_id** — UUID4 from the session-init command; mandatory so that “filter by current session” and semantic memory work (see §4.1).

Additional metadata (optional for v1): conversation_id, model name, round number — can be added later.

**Note:** Elsewhere in this plan (e.g. §4.2, worker, chunk linking), **message_id** denotes the value of the **uuid** field (the message identifier); the stored field name in Redis is **uuid**.

### 3.2a Described structure (schema) of the message store

- The **structure of the Redis message store** must be **described explicitly** (like the Database capability metric in §4.4f): field names, types, and purpose. This **schema description** ensures that clients, the worker, and the corporate DB share the same contract.
- Document in implementation: **RedisMessageRecord schema** — uuid (string, UUID4, primary key), created_at (string, ISO 8601), source (string, enum), body (string), session_id (string, UUID4). Optionally the schema can live in config or a dedicated Redis key (e.g. `message_schema`) for runtime discovery; minimum is documentation in code or docs.

### 3.3 Implementation notes

- **Container:** add Redis to the image (e.g. install and run `redis-server` in the same container) or use a Redis sidecar on the same network. Document how to enable/disable and how to configure connection (host, port, password if any).
- **Writer:** from the chat flow (or a small middleware around message handling), on each message push a record to Redis. Each record uses **uuid** (primary key), **created_at**, **source**, **body**, **session_id** (same names as chunk_metadata_adapter where applicable). Indices (e.g. by session_id) are secondary; key layout (e.g. key = `message:{uuid}`) and retention to be set in implementation.
- **chunk_metadata_adapter:** We do not use the full SemanticChunk model (separate project). Redis is for transmission/sync; field names **uuid**, **created_at**, **source**, **body** (and **session_id**) match so downstream and corporate DB stay consistent.
- **Vectors (embedding):** SemanticChunk has an **optional** `embedding` field; it does **not** imply storing the vector in Redis. For Redis we use the flat record **without** embedding. Embeddings are stored in the **vector table (DB)** (chunk_id, vector, vector_index_id) and in the **vector index** (e.g. FAISS) built from it; reindex rebuilds the index from the table (§3.5.4, §4.2a).
- **Scope:** “message stream” = messages that are part of the OLLAMA chat flow (user, assistant, tool). External agent can be added when such a source exists.

### 3.4 Summary (memory)

- Redis in container (or sidecar); used for **transmission and sync** with the corporate DB; field names aligned with **chunk_metadata_adapter** (SemanticChunk).
- **Schema:** The structure of the message store is **described explicitly** (§3.2a): field names, types, purpose — analogous to Database capability; document in implementation (and optionally in config or a schema key).
- Write to Redis for each message: **uuid** (primary key; message id; UUID4), **created_at** (ISO 8601 with timezone), **source** (user | model | tool | external_agent), **body** (message content), **session_id** (UUID4, mandatory). **No embedding** in Redis; vectors are in the **vector table (DB)** and in the vector index built from it (§3.5.4). Primary lookup by uuid; indices (e.g. by session) for listing.
- Exact key layout, stream vs list, and retention policy to be set during implementation.

### 3.5 Schema and structure of data stores (reference)

Consolidated description of all store schemas and structures used in the plan. Each store has an explicit **described structure** (field names, types, purpose) so that clients, workers, and external systems share the same contract.

#### 3.5.1 Redis message store (RedisMessageRecord)


| Field          | Type                            | Purpose                                                                            |
| -------------- | ------------------------------- | ---------------------------------------------------------------------------------- |
| **uuid**       | string (UUID4)                  | Primary key; message id. Same as SemanticChunk.uuid; chunk.source_id = this value. |
| **created_at** | string (ISO 8601 with timezone) | Message creation time.                                                             |
| **source**     | string (enum)                   | Origin: `user`, `model`, `tool`, `external_agent`.                                 |
| **body**       | string                          | Message content (text or JSON for tool calls/results).                             |
| **session_id** | string (UUID4)                  | Session scope; mandatory for “filter by session” and semantic memory.              |


- **Embedding:** Not stored in Redis (message stream). Vectors are in the **vector table (DB)** and in the vector index (e.g. FAISS) built from it; see §3.5.4.
- **Lookup:** Primary by uuid; secondary indices (e.g. by session_id) for listing. Schema must be documented in implementation (§3.2a); optionally in config or Redis key (e.g. `message_schema`).

#### 3.5.2 Session store (Session entity)


| Field                             | Type                        | Purpose                                                                                                                                                                                                                                                                                                       |
| --------------------------------- | --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **id**                            | string (UUID4)              | Session identifier (primary key).                                                                                                                                                                                                                                                                             |
| **model**                         | string                      | Model name/id for this session (e.g. `llama3.2`, `gemini-1.5-pro`). Required before context build; context window derived from it.                                                                                                                                                                            |
| **allowed_commands**              | list of string (command_id) | Optional; refines config policy for this session.                                                                                                                                                                                                                                                             |
| **forbidden_commands**            | list of string (command_id) | Optional; further restricts for this session.                                                                                                                                                                                                                                                                 |
| **created_at**                    | string or timestamp         | Optional; session creation time.                                                                                                                                                                                                                                                                              |
| **minimize_context**              | boolean                     | Optional; when true, after context is built and trimmed, optional parts (messages, relevance slot) are minimized until difference to last message starts to grow. Used to save tokens on commercial models. Set at session_init or session_update. **Redis:** stored as `"true"` / `"false"` in session hash. |
| **standards** / **session_rules** | —                           | Passed at session create; stored in **local Redis** (e.g. keyed by session_id); **can be updated**. Schema must allow storage and update (see §4.3).                                                                                                                                                          |
| (other)                           | —                           | user_id, metadata, external DBs for session, etc. as needed.                                                                                                                                                                                                                                                  |


- **Storage:** SessionStore interface; implementation can be SQLite, PostgreSQL, Redis-backed, etc. (§1.8). Standards and session rules: stored in local Redis; updatable.
- **Policy:** commands_policy (allow_by_default / deny_by_default) comes from **config**, not from session.

#### 3.5.3 External Database (capability descriptor)

An external **Database** (§4.4f) is described by a **capability metric** (descriptor), not by a single fixed table schema. The descriptor declares what the instance supports and how it can be queried.


| Aspect                | Description                                                                                                                                                                                   |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Search**            | semantic_search (by embedding; limit, relevance threshold), fulltext_search (e.g. BM25; limit, relevance), filter_by_pattern (ChunkQuery filter_expr; chunk_metadata_adapter FILTER_GRAMMAR). |
| **Access**            | write, read (one or set of records), search (semantic, full-text, by pattern). Not every instance supports all; declared per instance.                                                        |
| **Capability metric** | Flags or set: e.g. `semantic_search`, `fulltext_search`, `filter_by_pattern`, `read`, `write`. Optional: max_result_count, min_relevance, priority.                                           |
| **Query contract**    | chunk_metadata_adapter: ChunkQuery (filter_expr, search_query, search_fields, hybrid_search), FilterParser, FilterExecutor, FILTER_GRAMMAR.                                                   |


- **DatabaseManager** registers Database instances (with capability and optional priority); get by query (filter on properties/capabilities). Records in an external Database typically follow SemanticChunk-like shape (or a subset); exact record schema is defined by the external system; we only describe **how we query** (filter + semantic/BM25).

#### 3.5.4 Vector store (DB table) and vector index; chunk resolution by id; soft delete

- **Vector table (DB) schema:** **chunk_id** (UUID4, primary key — ensures uniqueness), **vector** (embedding), **vector_index_id** (integer; ID returned by FAISS when the vector is added — generated by the index each time). Optional: **is_deleted** (or **deleted_at**) — soft-delete flag; record is **marked** but not physically removed. **All reads and search result sets** filter out rows where is_deleted = true (or deleted_at IS NOT NULL); such rows are invisible to queries.
- **Add flow:** Chunk is added and vectorized; **vector and chunk are written to the DB first**. Then the vector is **added to FAISS**; the add procedure returns an **integer ID** (assigned by the index). That ID is stored in the table as **vector_index_id**. So: DB already has (chunk_id, vector); then add to FAISS → get back vector_index_id → update row with vector_index_id.
- **Soft delete (DB):** To "delete" a chunk, set the **deletion flag** (e.g. is_deleted = true or deleted_at = now). The row stays in the table; **no physical delete**. Every query (vector table reads, search path) **excludes** deleted rows (filter before sort/limit). UUID4 as primary key keeps chunk_id unique.
- **FAISS: no removal.** **Nothing is removed from the vector index** on soft delete. Records that are marked deleted in the DB are **excluded from results** at query time: after k-NN search (or when building the result list), **filter out** any chunk_id that has is_deleted in the DB — filter **before** sorting/limiting so deleted chunks never appear in the result set. So the index can still contain vectors for deleted chunks; they are simply not returned.
- **Reindex:** When **reindexing** FAISS, rebuild the index **only from non-deleted rows** in the vector table. After reindex, FAISS no longer contains the deleted vectors (they were not added to the new index). Optionally, physically remove or archive soft-deleted rows in the DB during or after reindex.
- **Chunk store / search: only chunk_id.** Body, source, session_id are **resolved by lookup** (chunk_id → message_id → Redis); can be implemented in **Redis Lua** or application code. BM25 store: chunk_id + tokens; same resolution and same **filter by is_deleted** if BM25 store has a deletion flag or is keyed by chunk_id and we check the vector table / common deleted set.

---

## 4. Context window and semantic memory

### 4.1 Session

- A **session** is started explicitly: a dedicated **command** (e.g. “start session” or “new dialogue”) is called with a **JSON** payload: **command name** (adapter command id), **parameters** (dictionary of session-record fields: model, allowed_commands, forbidden_commands, standards, session_rules, etc.). The response returns a **session identifier** — **UUID4**. The session is stored in the **database** with those attributes (see §1.8): id, model, allowed_commands, forbidden_commands, standards, session_rules, etc.
- **All requests** that participate in the same dialogue (chat, context build, memory lookup) must include this **session_id** as a **mandatory parameter**. No session is inferred from timeout or implicit boundaries; the client holds the session_id and sends it every time.
- Messages in Redis (and thus in semantic memory) are stored with this **session_id**. “Filter by current session” means: use only messages (and their chunks/vectors) whose session_id equals the one supplied in the request. The **effective tool list** for the model is computed from config + session (see §1.9).

### 4.2 Flow

- Messages are written to Redis (see §3) with **session_id**. A **separate process** (worker) consumes unvectorized data and calls the **chunker** (e.g. svo_client). The **chunker chunks and vectorizes in one go** (it calls the vectorizer internally); the worker receives chunks, BM25 tokens, and vectors from the chunker. The **embed/vectorizer client** (e.g. embed_client) is used **at query time** to obtain the **query embedding** for semantic search (not for indexing — indexing vectors come from the chunker).
- Each message has a **UUID4** (message id); tokens and vectors are linked to this ID. Messages are tied to a **session** via session_id. Together this forms **semantic memory**.
- To build the model context: (1) **semantic search** and/or **BM25 search** (see §4.2b); (2) **filter by current session** (session_id from request); (3) take **last N messages** for dialogue continuity. Combine into one context window.

### 4.2a Redis, vector table (DB), vector index (e.g. FAISS), and index update

- **Roles:** **Redis** holds the raw message stream (uuid, created_at, source, body, session_id; see §3). **Vector table (DB)** stores chunk_id, vector, optional vector_index_id; source of truth for embeddings; allows **reindexing** (rebuild k-NN index from table). **Vector index** (e.g. FAISS) is built from the vector table; used for k-NN search; filter by session_id (session_id resolved from chunk_id → message_id → Redis, or stored alongside chunk_id in the table if needed). **BM25/chunk store** holds chunk_id and tokens (and optionally message_id for linkage); no duplication of body/source/session_id — those are **resolved by lookup** (e.g. Redis Lua: chunk_id → message_id → get message by uuid).
- **Chunk resolution:** Only **chunk_id** is stored in the vector and BM25 stores. Body, source, session_id, created_at are **unwound** (resolved) by lookup: chunk_id → message_id (e.g. source_id) → Redis get message by uuid → return fields. Implementation can use **Redis Lua** for this (one round-trip: given chunk_id or message_id, return message fields) or application-level lookup.
- **Chunker:** The **chunker service** (e.g. svo-chunker; client: svo_client) **chunks and vectorizes** — it calls the vectorizer internally. The worker calls **only the chunker**; the chunker returns text chunks, BM25 tokens, and **vectors per chunk**. No separate worker→vectorizer call for indexing.
- **Embed/vectorizer client (query time):** The **embed client** (e.g. embed_client) is needed to obtain **vectors for the search query** when doing semantic search: given the query text, the client returns the query embedding, which is then used for k-NN search. So: chunker = index pipeline (chunk + embed in one go); embed client = query pipeline (embed the query only).
- **Worker flow:** (1) Read unprocessed messages from Redis; (2) for each message, call **chunker** → chunker returns chunks, BM25 tokens, and vectors (chunker invokes vectorizer internally); (3) write **vector table**: (chunk_id, vector); (4) **add to FAISS** → store returned vector_index_id; (5) update **BM25/chunk store**: chunk_id + tokens (and message_id for linkage); (6) mark message as processed in Redis.
- **Soft delete:** To delete a chunk, set **is_deleted** (or deleted_at) in the vector table; do **not** remove the row and do **not** remove the vector from FAISS. All queries exclude deleted rows (filter before sort/return). Deleted entries disappear from FAISS only at **reindex** (new index is built only from non-deleted rows).
- **Reindex operation:** Rebuild the vector index (e.g. FAISS) from the **vector table**, including **only non-deleted** rows. After reindex, FAISS no longer contains deleted vectors. Optional: physically delete or archive soft-deleted rows in the DB during/after reindex.
- **Index update strategy:** Incremental (worker adds to vector table and index as messages are processed) or batch; vector index can be rebuilt from the table when needed. Persistence: vector table and (optionally) persisted index; restarts can reload index from table.

### 4.2b Search methods: semantic and BM25

- **Semantic search (by vector):** Input: **query text** (or precomputed **query_embedding**), **session_id**, **top_k**. **Query embedding** is obtained by calling the **embed/vectorizer client** (e.g. embed_client) with the query text. Process: embed query → k-NN search on the vector index → candidate **chunk_ids** (and scores). **Filter out** chunk_ids that are marked deleted in the vector table (is_deleted = true) — filter **before** sort/limit so deleted chunks never appear. Then resolve body, message_id, session_id for each remaining chunk_id via lookup (e.g. Redis Lua). Return (chunk_id, message_id, session_id, score, text) to the context builder.
- **BM25 search (by tokens):** Same idea: get candidates from BM25 store; **exclude** chunk_ids that are deleted in the vector table (or in a shared deleted set); then resolve and return.
- **Resolution:** Non-key data (body, source, session_id) is **unwound** from Redis by chunk_id → message_id → get message; can be implemented in Redis Lua. Deleted chunks are excluded by **filter on is_deleted** before building the final result set.
- **Unified use:** The plan allows **unified relevance** (§4.4d): rank candidates from both semantic and BM25 (or from semantic only; BM25 can be used for hybrid scoring or as a fallback). Implementation may: (a) use only semantic search for the relevance slot; (b) use only BM25; (c) run both and merge/rerank (e.g. by weighted score or round-robin). Same embedding space requirement applies when combining with documentation chunks.

### 4.3 Context order (priorities) and context builder

The model context is filled in this order:

1. **Standards** — always at the beginning. **Source:** passed at session create, stored in **local Redis** (keyed by session_id); can be updated (see §1.8, §3.5.2).
2. **Session rules** — always at the beginning (after standards). **Source:** same as standards — passed at session create, stored in local Redis; can be updated.
3. **N messages** of recent history (fixed; always included; to preserve full dialogue picture).
4. **Relevance slot** — filled by **unified relevance** (see §4.4d): candidates from **session semantic chunks** and **documentation chunks** are ranked by vector distance to the current message; take items with **smaller distance** until the slot is full. Alternatively, fixed order: semantic slot then documentation block (§4.4a–4.4b).

**Context builder (separate object):** The **builder** that assembles the context is a **dedicated object** that uses, among other things, the **Redis client**. It assembles context from: (1) **Redis** — current message and history according to the rules defined in the steps (order above, N messages, slot sizing); (2) **session data** from the same Redis (standards, session rules, session metadata); (3) **external databases** specified for the session (e.g. list of Database instances or IDs in session). So: one builder object, fed by Redis (messages + session rules/standards) and by external DBs configured for the session.

### 4.4 Context size and semantic slot

- **Context size from session model:** The effective context window size is **determined by the model stored in the session**. For each request we have session_id → load session → get **model**; then look up that model’s context window (e.g. from OLLAMA API, or from a configurable model → window map). Effective **max_context_tokens** = **model_context_window** (or min(config max_context_tokens, model_context_window) if config sets a lower cap). **Effective limit = min(model_context_window, config max_context_tokens)** — we always choose the **smaller** value. The config parameter is the **overall context size limit** (resource cap for the service).
- Space reserved for **standards** and **session rules** is subtracted first. Let **remainder** = effective_limit − standards − session_rules − (N messages in tokens), where effective_limit = min(session model window, config max_context_tokens). Here max_context_tokens is the effective limit from the session’s model (and optional config cap).
- **Semantic slot:** from **min_semantic_tokens** up to **(remainder − min_documentation_tokens)** (see §4.4b). So semantics gets at least min_semantic_tokens and at most the remainder minus the space reserved for the documentation block.
- No separate “max %” for semantics: the upper bound is the remainder, so the last N messages are never pushed out by semantics or documentation.
- If **remainder < min_semantic_tokens** (i.e. after placing standards, rules, and N messages there is not enough space for the minimum semantic slot), **log an error** and **do not build / send the context** (or stop fetching messages for this request).

### 4.4a Documentation block: canon and clarifications

- **Documentation** is a separate context block filled **after** the semantic slot, in the remaining free space.
- Each documentation item has a **canon** flag (canonical / authoritative) and can be a **clarification** (уточнение) — supplementary or less authoritative.
- **Canon** — canonical documentation (e.g. project standards, API reference, approved specs). **Clarifications** — additional explanations, FAQs, non-canonical notes.
- Within the block, **strategy for adding**: canon first, then clarifications; ordering by relevance to the current query (or recency) to be defined in implementation. When space is limited: prefer canon over clarifications; truncate or drop lowest-priority items.

### 4.4b Strategy for adding documentation (sizing and placement)

- **Reservation:** Optionally reserve **min_documentation_tokens** from the remainder so that after the semantic slot there is at least this much space for documentation. Then **semantic slot** size = from **min_semantic_tokens** up to **(remainder − min_documentation_tokens)**; **documentation slot** = from **min_documentation_tokens** up to **(remainder − semantic_used)** (free space after semantics). If **min_documentation_tokens** is 0 or not set, documentation uses whatever remains after semantics (no guarantee; doc block can be empty if semantics fills the remainder).
- **Filling order:** (1) Add **canon** items first (by relevance or fixed order) until slot full or no more canon. (2) Add **clarifications** in the remaining space. If space is insufficient, drop lowest-priority (prefer canon over clarifications).
- **Sources of documentation:** Provided by a **pluggable backend** (see §4.4c); same mechanism for both pre-filling the doc block and for on-demand access via tool.

### 4.4c Documentation access mechanism (standardized tool + pluggable source)

- **Standardized tool(s)** expose documentation to the model in a uniform way, independent of the underlying source:
  - **Get table of contents (TOC)** — one call returns an index / list of available documentation items (e.g. titles, IDs, short descriptions, canon vs clarification). The model sees what is available without receiving full text.
  - **Get document content** — on request from the model (e.g. by ID or path), return the text of the selected item. So the model first calls TOC, then requests only the documents it needs; context and token use stay under control.
- **Pluggable source:** The backend that actually serves TOC and content is **configurable**. Examples:
  - **Directory (e.g. `docs/`)** — list files/subdirs as TOC; return file content by path. Gives the model the ability to "read files from docs" as one possible source.
  - **Vector database** — TOC could be a list of indexed doc/section IDs (or topics); content by ID or by semantic query (return top-k chunks). Same tool interface, different backend.
  - **Other stores** — API, CMS, static site generator output, etc. The adapter implements a common interface (e.g. `list_items(session_id?)` → TOC, `get_content(item_id)` → text); each backend implements that interface.
- **Integration with documentation block (§4.4a–4.4b):** The **context builder** can use the same backend to pre-fill the documentation slot (e.g. by relevance to the current turn, or fixed order) when building the context window. Alternatively or in addition, the **model** uses the tool during the dialogue to fetch TOC and then request specific content; that content can be appended to the conversation (e.g. as a tool result) rather than pre-injected. Both paths use the same source abstraction.
- **Config:** Backend type and connection details (e.g. `docs_path` for directory, vector DB URL and index name) in config; tool name(s) and parameters (e.g. `documentation_toc`, `documentation_content` with `item_id` or `path`) standardized so the model always sees the same interface regardless of source.

### 4.4d Unified relevance slot (documentation vs. conversation) — weak point addressed

- **Problem:** A fixed order “semantic slot → documentation slot” (or the reverse) arbitrarily prioritizes one over the other. Sometimes the current turn is more related to the **conversation** (session semantics), sometimes to **documentation**; we should not hard-code which wins.
- **Approach:** Use a **unified relevance slot** for “everything after N messages”. Candidates come from two pools: (1) **session semantic chunks** (past messages, vectorized and filtered by session_id), and (2) **documentation chunks** (canon + clarifications from the doc source). For the **current message** (or current turn), compute **vector distance** (or similarity) to each candidate. **Sort all candidates by distance** (smaller distance = more relevant). Fill the slot by taking items in order of **increasing distance** until the slot is full (or we run out of candidates). **N messages** are **always** included and **not** part of this competition; they stay in fixed order before this slot.
- **Result:** The model gets the most relevant content whether it comes from the conversation or from documentation. No fixed priority between doc and context; priority is **relevance to the current message**.
- **Requirement:** For a fair comparison, **documentation** and **session chunks** must be in the **same embedding space** (same model or compatible normalization). If documentation is embedded with model A and session with model B, distances are not directly comparable; either use one embedding model for both or define a comparable metric (e.g. both use the same vector DB and encoder).
- **Optional:** Config flag to choose behaviour: “unified by relevance” (above) vs. “fixed order” (semantic then doc, as in §4.4b) for deployments that prefer predictable ordering.

### 4.4e External data sources in the documentation part of context; priority

- **External sources:** The documentation part of context can include **external data sources** (in addition to or instead of a single DocumentationSource). Each external source is registered (e.g. via DatabaseManager) and has a **priority** (e.g. integer or level). When filling the relevance slot or documentation slot, among candidates with similar vector distance, the one from the **higher-priority** source is preferred.
- **Flow:** (1) Collect candidates from all sources (session semantic chunks, documentation backend(s), and **external databases**). (2) Rank all candidates by **vector similarity** (or hybrid score) to the current message; apply result count and relevance limits per source if defined. (3) When filling the slot, apply **source priority**: among candidates with similar relevance, take those from higher-priority sources first (or use priority as secondary sort). So: get all data, filter by vector closeness, then resolve ties by priority.
- **Entities:** External sources that expose search and optional read/write are modelled as **Database** (§4.4f); **DatabaseManager** registers them and returns databases by filter (e.g. by capability or priority).

### 4.4f Databases and Database manager (chunk_metadata_adapter as glue)

- **Database (база данных):** An external data source that can contribute to the documentation part of context. Each **Database** instance:
  - **Search:** Supports **semantic search** (by embedding; limit on result count and relevance threshold), **full-text search** (e.g. BM25; limit and relevance), and **filter-by-pattern** (structured filter over metadata). Filter syntax and execution align with **chunk_metadata_adapter**: ChunkQuery (filter_expr, search_query, hybrid_search), FilterParser, FilterExecutor, FILTER_GRAMMAR (SQL-like WHERE: LIKE, ~~, !~~, IN, INTERSECTS, comparison, AND/OR/NOT). The package is the **glue** between this project and chunk/vector services.
  - **Access:** Described by what the instance allows: **write**, **read** (one or set of records), **search** (semantic, full-text, by pattern). Not every database supports all; the description is part of the instance **capability metric**.
  - **Capability metric:** Each Database instance has a **capability metric** (descriptor) declaring what it supports: e.g. semantic_search, fulltext_search, filter_by_pattern, read, write. Limits (max result count, relevance threshold) can be part of capability or config. DatabaseManager can select databases by filter on these properties.
- **DatabaseManager (менеджер баз данных):** **Add** — register a Database (with capability metric and optional priority). **Remove** — unregister by id/handle. **Get by query** — return database(s) matching a filter on properties/capabilities (e.g. by capability flags, priority, name). Used by the context builder or RelevanceSlotBuilder to choose which external sources to query.
- **chunk_metadata_adapter:** Query and filter shape (ChunkQuery, filter_expr, search_query, FilterParser, FilterExecutor, FILTER_GRAMMAR) are the common contract between this project and chunk/vector backends. Use the same abstractions for pattern and full-text search so that external databases and the pipeline stay compatible.
- **Parser and filter language (chunk_metadata_adapter):** **FILTER_GRAMMAR** (Lark): SQL-like WHERE. **Operators:** =, !=, >, >=, <, <=; LIKE (substring); ~ / !~ (regex match / no match); IS NULL, IS NOT NULL; IN (value_list or array); INTERSECTS (list overlap); CONTAINS_KEY, CONTAINS_VALUE (dict); AND, OR, XOR, NOT; nested fields (e.g. `field.subfield`). **Values:** number, string (single/double quote), TRUE/FALSE, NULL/NONE, array `[...]`, dict `{...}`. **Classes:** FilterParser (string → AST), FilterExecutor (AST vs flat dict), FilterGrammarValidator (syntax/semantics), FilterGrammarExamples. **ChunkQuery:** filter_expr (AST), search_query (BM25), search_fields, hybrid_search; matches(chunk), get_ast(), validate().

### 4.5 Config (context)

- **max_context_tokens** — overall context size limit in config (resource cap for the service). **Effective limit = min(session model window, config max_context_tokens)**; we always take the smaller value.
- **last_n_messages** — integer; number of **messages** (not tokens) to always include in context (e.g. 10 or 20). Default to be set in config. Token count of these N messages is subtracted from remainder when computing slot size.
- **min_semantic_tokens** — minimum size reserved for semantic context (semantic slot is from this value up to remainder − min_documentation_tokens).
- **min_documentation_tokens** — optional; minimum size reserved for the documentation block (canon + clarifications). If set, semantic slot is capped so that this space remains for docs.
- **Documentation source** — backend type and connection (e.g. `docs_path` for directory like `docs/`, or vector DB URL/index, or other store); same backend used for pre-filling the doc block and for the standardized documentation tool (TOC + get content).
- **External data sources** — optional list or registry of external **Database** instances (via DatabaseManager) with priority; used to fill the documentation part of context; filter and query shape via chunk_metadata_adapter.
- **Relevance slot mode** — optional: `unified_by_relevance` (session and doc chunks compete by vector distance to current message; take smaller distance first) or `fixed_order` (semantic slot then documentation block). Default or recommended: unified_by_relevance when both pools use the same embedding model.
- Optionally: max size of standards block and session-rules block (in tokens or chars) so they do not overgrow.

### 4.6 Summary (context)

- **Redis and index:** Redis holds raw message stream; worker consumes, calls **chunker only** (chunker chunks and vectorizes internally); updates **vector index** (e.g. FAISS) and **BM25/chunk store**; index update incremental or batch (§4.2a). **Embed client** used at **query time** to get query embedding for semantic search.
- **Search methods:** **Semantic search** (embed query via embed client → query_embedding, session_id, top_k) and **BM25 search** (by query tokens, session_id, top_k); both return chunks with scores; used to fill relevance slot; implementation may use one or both, optionally hybrid (§4.2b).
- Semantic memory: Redis → worker → chunker (svo_client; chunker returns chunks, BM25, vectors); embed_client used for **query embedding** only; UUID per message; link to session.
- Context order: standards → session rules → **N messages** (always) → **relevance slot**. Relevance slot: either **unified by relevance** (§4.4d) — session chunks and doc chunks ranked by vector distance to current message, take smaller distance first — or fixed order: semantic slot then documentation block (§4.4a–4.4b).
- **Context size from session:** Effective context window is **determined by the model stored in the session**. Session has **model**; we look up that model’s context window and use it (or min with config cap). Effective limit = **min(session model window, config max_context_tokens)**; config is the resource cap, we choose the smaller value.
- Slot sizing: when fixed order, semantic slot min_semantic_tokens to (remainder − min_documentation_tokens), doc slot after; when unified, one slot filled by relevance (same embedding space for fair comparison). If remainder < min_semantic_tokens, log error and abort.
- **Documentation access:** Standardized tool returns TOC, then model requests content by id/path; source is pluggable (e.g. `docs/` directory, vector DB). Same backend used for pre-fill and for tool calls.
- **External data sources and priority (§4.4e):** The documentation part of context can include **external data sources** with a **priority** per source. Flow: collect from all sources → rank by vector similarity → apply source priority when filling the slot (higher priority preferred on tie). **Database** (§4.4f): external source with semantic search, full-text search, filter-by-pattern (chunk_metadata_adapter: ChunkQuery, FilterParser, FILTER_GRAMMAR); capability metric per instance; access (write, read, search) described in capability. **DatabaseManager:** add, remove, get database(s) by filter on properties/capabilities. chunk_metadata_adapter is the glue for query/filter contract.

---

## 5. Tools calling the model

### 5.1 Situation

Some tools may **invoke the model** (e.g. a command that delegates to a “sub‑agent”, summarises with the model, or is itself a chat call). Today **ollama_chat** is already such a tool: the proxy exposes it, and when the client calls it, the adapter runs the OLLAMA chat flow (model + tools). So we already have “tool → model”. The open design is: how to support this in a controlled way when **any** tool can trigger a model call (same or different endpoint), and how to pass session/context and avoid runaway recursion.

### 5.2 Risks

- **Recursion** — tool calls model → model calls tool → tool calls model → … Need a bounded depth or explicit “no model-calling tools” in nested calls.
- **Context explosion** — each nested call can add messages; without limits, context and cost grow quickly.
- **Session and memory** — nested model call should use the **same session_id** so semantic memory and “last N messages” stay consistent, but we must define what **context** we pass (full history vs. summary vs. only the tool input/result).
- **Ordering and latency** — nested calls are synchronous (tool waits for model reply); deep nesting can make response time high.

### 5.3 Call stack and recursion depth

- **Call stack:** For each request (or for the duration of the chat flow within a session), maintain a **call stack**. Each entry represents one “model invocation” frame. Example: stack of `(tool_name, depth)` or `(call_id, depth)`.
- **Depth:** Depth 0 = top-level chat (no tool triggered this call). When a **model-calling tool** (e.g. `ollama_chat`) runs, it starts a nested model invocation at **depth = current_depth + 1**; push that frame onto the stack. When the nested invocation returns, pop the frame.
- **Limit:** Config **max_model_call_depth** (e.g. 1 or 2). Before starting a model invocation from a tool, check: if **current_depth >= max_model_call_depth**, do **not** call the model; return an error to the caller (e.g. `"max recursion depth exceeded"` or `"nested model calls not allowed at this depth"`). This bounds recursion.
- **Stack lifecycle:** Stack is created at the entry point (e.g. first `ollama_chat` for this request). Push on entering a model call from a tool, pop on return. Stack is discarded when the top-level flow completes.

### 5.4 Options (to be agreed)

**A. Session and context for nested call**

- **session_id** — always pass the **same** session_id into any nested model call so that Redis, semantic memory, and “filter by session” refer to one dialogue.
- **Context passed in** — one of:
  - **Full history** — nested call receives the same message history as the current level (plus the tool request). Simple but can double context and confuse “who is replying to whom”.
  - **Sub-context** — nested call receives: system prompt (or summary) + “Tool X requested: …” + optional last K messages. Keeps context smaller and scoped to the tool’s need.
  - **Tool-only** — nested call receives only the tool’s input (and maybe a short system line). Minimal context; model may lack dialogue continuity unless we inject a short summary.

**B. Which tools may call the model**

- **Allow-list** — only certain commands (e.g. `ollama_chat`, a dedicated `ask_model` tool) are allowed to trigger a model call; others are plain RPC. Easy to enforce and reason about.
- **Generic** — any tool can request “call model” (e.g. via a special parameter or a side-channel). More flexible but harder to guard (depth, cost, context).

**C. Identity of the “caller” in Redis**

- When a tool invokes the model, the resulting messages (user, assistant, tool) should be stored in Redis with **session_id** and a way to associate them with the **parent** call (e.g. parent_message_id or call_depth) so that semantic memory and analytics can distinguish top-level vs. nested turns.

### 5.5 Recommendation (draft)

- **Depth:** Introduce **max_model_call_depth** (e.g. 1); if a tool at max depth tries to call the model, return an error or a fixed “nested calls not allowed” message.
- **Session:** Always use the **same session_id** for nested model calls.
- **Context:** Use **sub-context** for nested calls: inject a short “Tool X requested: …” plus optional last K messages (or a summary), not the full history, to keep context size and cost under control.
- **Allow-list:** Only tools explicitly designated as “can call model” (e.g. `ollama_chat`) are allowed to trigger a model invocation; others are non-model tools.
- **Redis:** Store all messages (including from nested calls) with session_id and optionally parent_message_id or depth so that “last N messages” and semantic search can be defined per level or globally for the session.

### 5.6 Summary

- Tools can invoke the model; we need a clear rule for depth, session/context, and which tools may do it.
- Propose: max depth 1 (configurable), same session_id, sub-context for nested call, allow-list of “model-calling” tools, and Redis records that link nested messages to the session (and optionally to the parent call).

---

## 6. Code quality and step success metrics

All implementation steps must satisfy project code quality and step-level checks.

### 6.1 Tooling (aligned)

- **black** — formatting; `line-length = 88` (see `pyproject.toml`).
- **flake8** — lint; `max-line-length = 88` (aligned with black). Run: `flake8 src tests`.
- **mypy** — static typing; `python_version = "3.12"`, `warn_return_any`, `warn_unused_ignores`, `ignore_missing_imports = true` (see `pyproject.toml`).
- **code_mapper** — after each batch of file changes: `code_mapper -r src`; fix all reported errors.

### 6.2 Per-step success metrics

Each step document in [docs/plans/dynamic_commands_memory/](dynamic_commands_memory/) MUST include:

1. **Step-specific parameters and checks** — config fields, object invariants, acceptance criteria that are verified for that step.
2. **Standard verification** (after writing code):
  - No incomplete code, TODO/FIXME left in production code, ellipsis (`...`) or syntax violations.
  - No `pass` except in exception classes or stub blocks; no `NotImplemented` except in abstract methods.
  - No deviations from project rules (see [docs/RULES.md](RULES.md), [.cursor/rules/project-standards.mdc](.cursor/rules/project-standards.mdc)) or from this plan.
  - Run `code_mapper -r src` and fix all errors.
  - Run `mypy src`, `flake8 src tests`, `black --check src tests` (or `black src tests` to fix) and fix all issues.

### 6.3 File size and structure

- One class per file (except small enums/exceptions). Max 350–400 lines per file; split when exceeded.
- Imports only at top of file (except lazy loading). File header: Author, email.

### 6.4 Config generator and validator (project vs adapter)

- **Principle:** The project uses the **adapter’s config generator and validator as the base**. Project-specific config is applied **on top**: (1) **Generator:** call adapter’s `SimpleConfigGenerator.generate(...)` first, then patch the generated JSON with project sections (e.g. `ollama_workstation`, `transport`, server overrides). (2) **Validator:** run adapter’s `SimpleConfig.load()` and `SimpleConfig.validate()` first, then run **project-specific validation** (`validate_project_config(app_config)`) on the same config dict. No duplication of adapter schema; project only adds and validates its own fields.
- **When adding new config:** Any step that introduces new config fields (e.g. step 01: commands policy; step 05: session store; step 09: Redis; step 10: context; step 12: max_model_call_depth) MUST also:
  - **Config generator** (e.g. `docker/generate_config.py`, `container/generate_config.py`): add the new fields to the project overlay (e.g. under `ollama_workstation` or the appropriate section) so that generated `adapter_config.json` contains defaults or placeholders for the new options.
  - **Project-specific validator** (`validate_project_config` in `src/ollama_workstation/docker_config_validation.py`): add validation for the new fields (e.g. enum for `commands_policy`, list types for `allowed_commands`/`forbidden_commands`) and return error messages for invalid values.
  - **Config loader / model** (e.g. `WorkstationConfig`, `CommandsPolicyConfig`, or config loader in `config.py`): load and expose the new fields; validation in loader or in `validate_project_config` as appropriate.
  - **Example config** (e.g. `config/ollama_workstation.example.yaml`): document the new options.
- This keeps generated configs and validation consistent and ensures the adapter remains the single source of truth for adapter schema; the project only extends it.

---

## 7. Deliverables (reference)

- **Commands:** Config schema and code for allowed/forbidden/policy; discovery and build of dynamic command list; safe name translation and registry; command registry and aliases per model; integration with tools array; agreement on update strategy. **Session store** (DB) with session id, **model**, allowed_commands, forbidden_commands; **commands** to add/remove command from session (reject and log if adding a config-forbidden command); config lists and policy override session lists; effective tool list = merge(config, session).
- **Context representation:** Base class for representation with virtual methods; derived classes per provider (OpenAI, Anthropic, Ollama, Opera AI, etc.); registry model → representation type; on session model change: context preserved, trimmed to new window if needed, representation swapped.
- **Memory:** Redis in container (or deployment doc for sidecar); writer that records uuid, created_at, source, body, session_id (UUID4) for each message (field names aligned with chunk_metadata_adapter); session initiated by a command that returns session_id; all requests carry session_id as mandatory parameter.
- **Tools → model:** Call stack + max recursion depth (config); enforce depth before invoking model from a tool; agreement on context shape for nested calls, allow-list of tools that may call the model, and Redis shape for nested messages; then implementation.

---

## 8. Analysis and conclusions

### 8.1 What is covered


| Area                       | Covered | Notes                                                                                                                                                                                                                                                                                                                                                      |
| -------------------------- | ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Dynamic commands**       | Yes     | Discovery from proxy, Command.ServerId, allow/forbidden/policy; safe names and registry; aliases per model; **update strategy: dynamic** (§1.2, step_03 — startup + periodic, mark unavailable). Session store (DB) with model, allowed/forbidden per session; add/remove command to session (reject + log if config-forbidden); config overrides session. |
| **Context representation** | Yes     | Base class + per-provider representations; registry model → representation type; on model change: context preserved, trimmed, representation swapped (§2).                                                                                                                                                                                                 |
| **Redis message stream**   | Yes     | uuid, created_at, source, body, session_id (aligned with chunk_metadata_adapter); container or sidecar.                                                                                                                                                                                                                                                    |
| **Session**                | Yes     | Explicit start via command (returns UUID4); session_id mandatory in all requests.                                                                                                                                                                                                                                                                          |
| **Semantic memory**        | Yes     | Worker + chunker (chunks and vectorizes; e.g. svo_client); embed client for query embedding only; → BM25, vectors, chunks; message UUID; link to session.                                                                                                                                                                                                  |
| **Context window**         | Yes     | Order: standards → session rules → N messages → **relevance slot**. Slot: **unified by relevance** (session + doc chunks ranked by vector distance to current message; take smaller distance) or fixed order (semantic then doc); same embedding space for fair comparison; N messages always included.                                                    |
| **Tools calling model**    | Yes     | Call stack, max depth, same session_id, sub-context, allow-list, Redis with parent/depth.                                                                                                                                                                                                                                                                  |


### 8.2 Gaps and open points / weak points addressed

- **Priority documentation vs. conversation (addressed in §4.4d):** Fixed order “semantic then doc” was a weak point. We add a **unified relevance slot**: candidates from session semantics and documentation are ranked by **vector distance to the current message**; we take items with **smaller distance** until the slot is full. N messages stay fixed. For fair comparison, both pools must use the **same embedding space**. Optional config: “unified by relevance” vs. “fixed order”.
- **Update strategy for commands** (§1.2) — **resolved:** dynamic — on startup + periodic (`command_discovery_interval_sec`); mark commands unavailable when server unreachable. See step_03.
- **Exact Redis layout** — key format, STREAM vs LIST, TTL, retention. Planned for implementation phase.
- **Standards / session rules** — **resolved:** passed at session create, stored in local Redis (keyed by session_id); can be updated; schema §3.5.2. Token size for remainder as in §4.3/§4.5. See 14_ambiguities #4.
- **Documentation block** — selection and ranking for pre-fill; API or config for listing docs per session/project. **Documentation access** is covered by §4.4c: standardized tool (TOC + get content), pluggable source (e.g. docs/ directory, vector DB); implementation defines exact tool names and backend interface.
- **N (last N messages)** — resolved: config parameter **last_n_messages** (integer, message count); default e.g. 10 or 20; see §4.5 and [dynamic_commands_memory/14_ambiguities_and_open_points.md](dynamic_commands_memory/14_ambiguities_and_open_points.md).
- **Chunker** (e.g. svo_client) — chunks and vectorizes in one go (calls vectorizer internally); worker calls chunker only. **Embed client** (e.g. embed_client) — used at **query time** to get query embedding for semantic search. Existing clients; auth, retries, and behaviour when unavailable aligned with those clients.
- **Session-init command** — **resolved:** JSON request (command name, **parameters** = session record fields: model, allowed_commands, forbidden_commands, standards, session_rules); response includes session_id. See step_13 and 14_ambiguities #12.
- **Session-update command** — **SessionUpdateCommand** in step_13: session_id, optional model, allowed_commands, forbidden_commands; can also update standards, session_rules (per §3.5.2). Session-init format in step_13.
- **Session DB** — choice of DB (SQLite / PostgreSQL / Redis) and schema (id, **model**, allowed_commands, forbidden_commands, created_at, etc.); where it runs (same container vs. external). Model → context window lookup (e.g. from OLLAMA or a table) to be implemented.
- **Recommendation §5.5** — “Depth” bullet still says “Introduce max_model_call_depth” but does not reference call stack; §5.3 already defines stack. Minor: align wording so Recommendation explicitly says “maintain call stack (see §5.3), enforce max depth”.

### 8.3 Risks (recap)

- **Dependency on chunker and embed client** — chunker (index pipeline) and embed client (query embedding); if chunker is down or slow, indexing is delayed; if embed client is down, semantic search cannot produce query embedding; retry/backoff and behaviour (e.g. context without semantics, or fail request) follow client capabilities.
- **Redis and worker** — if Redis is full or worker crashes, unvectorized messages may pile up; consider queue limits and monitoring.
- **Context build failure** — when remainder < min_semantic_tokens we abort; the client (e.g. Cursor) should get a clear error and optional fallback (e.g. “context build failed: standards+rules+N exceed limit” or “reduce N / shorten standards”).

### 8.4 What we get in the end

**System behaviour:**

1. **Unified tool surface** — The model sees one flat list of tools (Command.ServerId) from all proxy servers, with allow/forbid and policy. No need to “first list_servers, then call_server”; the model can call e.g. `chunk.svo-chunker` or `ollama_chat.ollama-adapter` directly (if permitted).
2. **Session-based dialogue** — Every dialogue is explicitly tied to a session_id (UUID4). All messages and semantic memory are scoped by session; context and memory lookups use the same session.
3. **Semantic memory** — Messages are stored in Redis; a worker uses the **chunker** (which chunks and vectorizes in one go) to produce chunks, BM25 tokens, and embeddings per message (by UUID). **Query embedding** for semantic search is obtained via the **embed client**. Retrieval is by semantics, then filtered by current session, so the model gets relevant past content within the same dialogue.
4. **Controlled context** — Context order: standards → session rules → **N messages** (always) → **relevance slot**. The relevance slot can be filled by **unified relevance** (session chunks and documentation chunks ranked by vector distance to the current message; take smaller distance first) so that documentation vs. conversation priority is not fixed but **relevance-driven**. Alternatively, fixed order (semantic then doc). Max size and minimum semantics (or unified slot size) enforced; if remainder too small, request fails with clear error.
5. **Safe tool→model recursion** — When a tool invokes the model, we keep a call stack and enforce max depth. Same session_id and sub-context are used for nested calls; only allow-listed tools can trigger the model. Recursion is bounded and observable (stack/depth in Redis if needed).

**Deliverables (summary):**

- Config and code for dynamic commands (discovery, allow/forbidden, policy) and their update. Session store (DB) with id, **model** (used to determine context window size for the session), allowed_commands, forbidden_commands; commands to add/remove command from session (reject and log if adding config-forbidden); effective tool list = merge(config, session), config has priority.
- Redis in container (or sidecar), writer for message stream (uuid, created_at, source, body, session_id; aligned with chunk_metadata_adapter).
- Session-init command returning session_id (and accepting **model** to set for the session); all chat/context requests require session_id. **Context size** = from session’s model (look up model’s window); effective limit = min(session model window, config max_context_tokens) — resource cap; we choose the smaller value.
- Worker process that reads from Redis, calls **chunker** (chunker chunks and vectorizes; e.g. svo_client), and stores/indexes vectors and chunks per message (and session). **Embed client** used at query time for query embedding.
- Context builder: standards + session rules + N messages + semantic slot + **documentation** (canon + clarifications in free space after semantics); config for max_context_tokens, min_semantic_tokens, min_documentation_tokens (optional), N; strategy for filling doc block (canon first, then clarifications); error when remainder < min_semantic_tokens. **Documentation access:** standardized tool(s) — TOC + get content by request; pluggable source (e.g. `docs/` directory, vector DB, or other store); same backend for pre-fill and for tool calls.
- Call stack and max_model_call_depth for tool→model calls; allow-list of model-calling tools; sub-context and Redis shape for nested messages.

**Conclusion:** The plan is coherent and covers dynamic commands, Redis stream, session, semantic memory, context window (with **unified relevance slot** for documentation vs. conversation), documentation access (TOC + get content, pluggable source), and tool→model recursion. **Weak point addressed:** priority between documentation and conversation is not fixed; we compare vector distance of (documentation, current message) and (session, current message) and take the **smaller distance** (more relevant), except for the N messages which are always included. Same embedding space required for fair comparison. Main open work: (1) command list update strategy **defined** (§1.2, step_03); (2) define Redis key/stream layout (chunker and embed client use existing clients); (3) standards/session rules **defined** (at session create, Redis, updatable §3.5.2, 14_ambiguities #4); (4) session-init contract **defined** (JSON, step_13, 14_ambiguities #12); (5) implement unified relevance merge (one embedding model for both session and doc chunks). Implementation can proceed in phases (e.g. Redis + writer → session + context build → worker + chunker (existing client) + embed client at query time → dynamic commands → call stack + depth → unified relevance slot).

### 8.5 Readiness for AI-led implementation

- **Scope:** Steps 01–13 are specified with Goal, Objects, Inputs/outputs, Acceptance criteria, References (plan § and step links), Success metrics, Dependencies, Deliverable. Schema reference: §3.5; config rules: §6.4; code quality: §6.
- **Resolved:** Command update strategy (§1.2, step_03), standards/session rules (#4), session-init format (#12), chunker/embed roles (§10), soft delete/reindex (9f), config generator/validator (§6.4). Single remaining **TBD at implementation:** #10b (ContextBuilder message source: Redis client vs MessageStore abstraction — document in step_10 impl).
- **Implementation-phase choices** (no block for AI): Redis key layout (STREAM vs LIST, TTL); Session DB choice (SQLite/PostgreSQL/Redis) and where it runs; §5.4 options (nested call context shape) — follow §5.5 Recommendation.
- **Verdict:** **Ready for handover to AI.** Execute in order step_01 … step_13; use README checklist for chat flow wiring; run black, flake8, mypy, code_mapper after each step. For steps that add config, extend generator overlay and `validate_project_config` per §6.4.

