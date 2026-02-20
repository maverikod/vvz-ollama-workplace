# Ambiguities and open points

**Author:** Vasiliy Zdanovskiy  
**Email:** vasilyvz@gmail.com  

This document lists ambiguities and open points identified in the [Dynamic commands and Redis memory](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md) plan and step files, and records resolutions or "to be defined" (TBD) decisions.

---

## 1. Command list update strategy

- **Issue:** Main plan §1.2 left update strategy to be agreed; step 03 deferred the choice.
- **Resolution:** **Dynamic:** (1) **On startup** — fetch list from proxy. (2) **Periodically** — refresh from the same proxy; add **config** `command_discovery_interval_sec` for the check interval. (3) When a server is **unavailable** — **mark that server's commands as unavailable** (do not remove from the list). Main plan §1.2 and §1.4; step_03 updated.

---

## 2. allow_by_default and allowed_commands

- **Issue:** Main plan §1.4: under `allow_by_default`, "If allowed_commands is set, it can be ignored or used as an additional filter (to be defined)."
- **Resolution:** Define explicitly. Recommended: under **allow_by_default**, if `allowed_commands` is non-empty, treat it as an **additional allow-list** (intersection): only commands that are both discovered and in `allowed_commands` pass, minus `forbidden_commands`. If `allowed_commands` is empty, expose all discovered minus forbidden. This keeps behaviour predictable and allows "allow_by_default but restrict to this list".

---

## 3. Last N messages — config name and units

- **Issue:** Plan §4.3 and §4.5 refer to "N messages" but do not define the config parameter name, default value, or whether N is message **count** or **tokens**.
- **Resolution:** Add to config (and step_10): **last_n_messages** (or **n_recent_messages**): integer, number of **messages** (not tokens) to always include. Default: e.g. 10 or 20. Token count of these N messages is subtracted from remainder when computing slot size.

---

## 4. Standards and session rules — source and size

- **Issue:** Where standards and session rules are stored and how they are loaded was not defined.
- **Resolution:** **Standards and session rules** are **passed at session create** as arguments (e.g. in session-init parameters) and **stored in local Redis** (session store / session-scoped keys). They **can be updated** (e.g. via SessionUpdateCommand or a dedicated update). Schema (main plan §3.5.2) and session record must reflect updatable standards/session_rules. Token size for remainder: as in plan (config or tokenizer); source = Redis for the current session.

---

## 5. Session model: required at create vs optional

- **Issue:** Step 05 says model is "optional at create; can be set later". Context build (§4.4) requires session.model to compute effective_limit; if model is missing, behaviour is undefined.
- **Resolution:** (1) **At create:** model may be optional; if omitted, session is created with model = null or default. (2) **Before first context build or chat:** model must be set (e.g. via session-update or first chat request that supplies model). If context build or chat is called with session.model unset, return a clear error ("session model not set; set model via session update or init"). Document in step_05 and step_13.

---

## 6. Session update (set model) command

- **Issue:** Diagram in 00_objects_and_diagrams (§7) shows "set_session_model(session_id, new_model)" and main plan §2.3 describes changing model later. Step_13 only defines SessionInitCommand, AddCommandToSessionCommand, RemoveCommandFromSessionCommand — no explicit "set model" or generic session-update command.
- **Resolution:** Add **SessionUpdateCommand** (or **SetSessionModelCommand**): parameters session_id, optional model, optional allowed_commands, optional forbidden_commands. Allows setting model and optionally updating lists. Document in step_13 and in 00_objects_and_diagrams (SessionUpdateCommand or extend SessionInitCommand to "session create/update" if preferred). Prefer explicit SessionUpdateCommand for clarity.

---

## 7. Display name uniqueness (alias collision)

- **Issue:** Effective tool list requires unique display_name per tool (for ToolCallRegistry). If two different command_ids are given the same alias for a model, or if safe names ever collide, resolution is ambiguous.
- **Resolution:** (1) **Aliases:** When building the effective list, if an alias is already used by another command for this session, treat as configuration error: log and either skip that alias (fall back to safe name) or fail the build. Recommend: **alias must be unique per (session, model)**; if duplicate, log warning and use safe name for the duplicate. (2) **Safe names:** command_id is unique, and safe name is deterministic from command_id, so safe names are unique if command_ids are unique. Document in step_04 (alias uniqueness) and step_06 (validation at build time).

---

## 8. Model → context window size lookup

- **Issue:** Effective limit = min(session model window, config max_context_tokens). Where does "session model window" come from (OLLAMA API, config table, constant)?
- **Resolution:** Main plan **§2.5 Per-model scheme** now specifies for **Ollama** and **Google (Gemini)**:
  - **Context size:** Ollama — from OLLAMA API (`/api/show`), config map `model_context_windows`, or default; Google — from config map or family/default (e.g. gemini-1.5-* → 1M). Effective limit = min(model window, config max_context_tokens).
  - **Representation:** Ollama — OllamaRepresentation (tools: type "function", function name/description/parameters; messages: role + content + tool_calls/tool results); Google — GoogleRepresentation (tools: FunctionDeclaration; messages: role + parts with text/functionCall/functionResponse). Registry maps model_id → representation; lookup flow in §2.5.3.

---

## 9. Redis key layout and retention

- **Issue:** Main plan §3.4 and step_09 leave exact key format, LIST vs STREAM, and TTL/retention to implementation.
- **Resolution:** Acceptable as implementation-phase decision. Step_09 already requires "key layout and structure documented". Ensure implementation doc defines: key pattern (e.g. by session_id), structure (LIST vs STREAM), and retention/TTL policy.

## 9a. Message id as primary key (get message by id)

- **Issue:** Plan §4.2 says each message has a message id; it was unclear whether Redis records must allow retrieving the full message by id.
- **Resolution:** The **primary key field** is **uuid** (same name as chunk_metadata_adapter SemanticChunk.uuid); the value is the message id. By uuid the full message (created_at, source, body, session_id) must be assemblable. Indices (e.g. by session_id) are secondary. Main plan §3.2 and step_09 use **uuid**, **created_at**, **source**, **body**, **session_id** (aligned with chunk_metadata_adapter). Elsewhere in the plan, "message_id" (e.g. in worker, chunk linking) refers to the value of the uuid field.

## 9b. chunk_metadata_adapter integration (Redis field names)

- **Issue:** Redis is used for transmission and sync with the permanent corporate database; the full semantic-chunk pipeline is a separate project. We need consistent property names with chunk_metadata_adapter (SemanticChunk) so that our records can be consumed by the corporate DB and existing clients without renaming.
- **Resolution:** Redis message record uses the **same field names** as SemanticChunk where applicable: **uuid** (primary key; message id), **created_at** (ISO 8601 with timezone; replaces generic "timestamp"), **source**, **body**. We add **session_id** (not in SemanticChunk) for session scope; corporate DB may map it to project or a column. We use only the subset of fields we need; we do not use the full SemanticChunk model. Main plan §3 and step_09 updated.

## 9c. External data sources, Database, DatabaseManager (documentation context)

- **Issue:** The documentation part of context may need to include **external data sources** with **priority** (e.g. collect from all → rank by vector similarity → keep higher-priority on tie). A unified notion of **Database** (semantic + full-text + filter-by-pattern; capability metric; write/read/search access) and **DatabaseManager** (add, remove, get by filter) was missing.
- **Resolution:** Main plan **§4.4e** and **§4.4f** added. **§4.4e:** External data sources in the documentation part of context; each source has a **priority**; flow: collect from all sources → rank by vector similarity → apply source priority when filling the slot. **§4.4f:** **Database** — semantic search, full-text search, filter-by-pattern (chunk_metadata_adapter: ChunkQuery, FilterParser, FilterExecutor, FILTER_GRAMMAR); per-instance **capability metric**; access (write, read, search) described in capability. **DatabaseManager** — add, remove, get database(s) by filter on properties/capabilities. **chunk_metadata_adapter** is the glue between projects for query/filter contract. 00_objects_and_diagrams and step_11 reference these; optional implementation in step_11 or a later step.

## 9d. Redis: described structure (schema) and embedding not stored

- **Issue:** (1) Should the Redis message store have an explicit **described structure** (schema), similar to how we describe a Database (capability metric)? (2) Does SemanticChunk imply **passing/storing the vector** in Redis?
- **Resolution:** (1) **Yes.** The structure of the Redis message store must be **described explicitly** (field names, types, purpose) — analogous to Database capability — so clients and corporate DB share the same contract. Main plan **§3.2a** added: RedisMessageRecord schema (uuid, created_at, source, body, session_id); document in implementation; optionally in config or a schema key. (2) **No.** SemanticChunk has an **optional** `embedding` field; it does **not** imply storing the vector in the Redis message stream. chunk_metadata_adapter uses `to_flat_dict(for_redis=True, include_embedding=False)` for Redis; embeddings are stored in the **vector table (DB)** and vector index, not in Redis. Main plan §3.3 and §3.4 updated.

## 9e. Chunk store: only chunk_id; vectors in DB; reindex

- **Issue:** (1) Should the chunk/vector store keep only the **chunk identifier**, with the rest (body, source, session_id) resolved by lookup (e.g. Redis Lua)? (2) Should **vectors be stored in a DB table** with an explicit **reindex** operation (table: chunk_id, vector, vector_index_id)?
- **Resolution:** (1) **Yes.** Only **chunk_id** (and vector/tokens) is stored in the vector and BM25 stores. Body, source, session_id are **resolved by lookup**: chunk_id → message_id (source_id) → get message from Redis → return fields. Implementation can use **Redis Lua** (one round-trip) or application code. Main plan §3.5.4 and §4.2a, §4.2b updated. (2) **Yes.** Vectors are stored in a **vector table (DB)**: chunk_id (PK), vector, vector_index_id (integer from FAISS add). Reindex rebuilds k-NN index from the table. See also 9f (soft delete, filter, reindex removes deleted from index).

## 9f. Soft delete in vector table; no removal from FAISS; filter and reindex

- **Issue:** How to handle chunk deletion: physical delete vs soft delete? Should FAISS be updated on delete?
- **Resolution:** **Soft delete** in the vector table: add **is_deleted** (or deleted_at). Rows are **marked** but not removed; **all queries** filter them out (deleted rows are invisible). **FAISS:** do **not** remove vectors from the index on delete. At **query time**, after k-NN search, **filter out** chunk_ids that are marked deleted in the DB — filter **before** sort/limit so deleted chunks never appear in results. **Reindex:** when rebuilding FAISS from the table, include **only non-deleted** rows; after reindex, FAISS no longer contains the deleted vectors. Optionally purge soft-deleted rows from the DB during/after reindex. Main plan §3.5.4, §4.2a, §4.2b updated.

---

## 10. Chunker and vectorizer (chunker does both; embed client for query)

- **Issue:** Plan §4.2 referred to chunker and vectorizer; API contract and who calls whom were not specified.
- **Resolution:** The **chunker** (e.g. svo-chunker, client: svo_client) **chunks and vectorizes in one go** — it calls the vectorizer internally. The worker calls **only the chunker** for the index pipeline; the chunker returns chunks, BM25 tokens, and vectors. The **embed/vectorizer client** (e.g. embed_client) is used **at query time only** — to obtain the **query embedding** for semantic search (embed the search query text). So: chunker = index (chunk + embed); embed client = query (embed the query). Main plan §4.2, §4.2a, §4.2b, §4.6 updated accordingly.

## 10a. Redis ↔ vector index (e.g. FAISS) and index update

- **Issue:** How Redis and the vector/BM25 index interact and how the index is updated was not specified; FAISS was not mentioned.
- **Resolution:** Main plan §4.2a added: Redis holds raw messages; worker reads unprocessed messages, calls **chunker only** (chunker returns chunks, BM25, vectors); writes vectors to vector index (e.g. FAISS) and BM25/chunk data to a store; marks processed. **Embed client** used at query time to get query embedding for semantic search. Update strategy: incremental or batch; persistence of index and store required. §4.2b: semantic search uses embed client for query_embedding, then k-NN; BM25 by tokens; both with session_id filter and top_k.

## 10b. ContextBuilder message source

- **Issue:** Step_10 says "load messages from Redis/semantic store"; it is unspecified whether ContextBuilder uses a Redis client directly or a thin abstraction (e.g. MessageStore.get_messages(session_id)).
- **Resolution:** **Closed.** We use a **MessageStore** abstraction (interface `get_messages(session_id)`). ContextBuilder depends on MessageStore only; default implementation is **RedisMessageStore** (reads from Redis). Documented in `src/ollama_workstation/message_store.py` and `context_builder.py`.

---

## 11. RelevanceSlotBuilder — full implementation vs stub

- **Issue:** Step_10 assigns RelevanceSlotBuilder to context builder but says "stub or minimal RelevanceSlotBuilder if unified slot is deferred". 00_objects_and_diagrams marks "unified relevance slot implementation" as "optional / later".
- **Resolution:** Step_10 deliverable: for **first implementation** use **fixed-order only** (semantic slot then documentation block); add config flag `relevance_slot_mode` (fixed_order | unified_by_relevance). Full unified ranking in a later phase when embedding and chunker are available. Documented in step_10.

---

## 12. Session-init command name and response shape

- **Issue:** Step_13 did not fix the exact request/response format for session-init.
- **Resolution:** **Format: JSON.** (1) **Request:** **command name** (adapter command id), **session identifier** (omitted on create; returned in response), **parameters** — dictionary with fields from the session record/DB (e.g. model, allowed_commands, forbidden_commands, standards, session_rules). (2) **Response:** e.g. `{ "session_id": "<uuid4>" }`. Documented in step_13 and main plan where session-init is described.

---

## 13. Config generator and validator (cross-cutting)

- **Issue:** The plan introduces many new config fields (step 01: commands policy; step 05: session store; step 09: Redis; step 10: context; step 12: max_model_call_depth, allow-list). It was not explicitly stated that the **config generator** and **project-specific validator** must be updated for each new config block, and that both must remain **based on the adapter** (adapter first, project on top).
- **Resolution:** Main plan [§6.4 Config generator and validator](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#64-config-generator-and-validator-project-vs-adapter) added. Rule: (1) **Generator:** use adapter’s `SimpleConfigGenerator` first, then apply project overlay (e.g. `docker/generate_config.py`). When a step adds new config, extend the generator’s overlay so generated `adapter_config.json` includes the new fields (with defaults). (2) **Validator:** run adapter’s `SimpleConfig.validate()` first, then `validate_project_config(app_config)`. When a step adds new config, extend `validate_project_config` (in `src/ollama_workstation/docker_config_validation.py`) to validate the new fields. Step 01 explicitly requires updating both; steps 05, 09, 10, 12 should do the same when they introduce config (session store type, Redis connection, context params, max_model_call_depth, allow-list).

---

## Summary

| # | Topic | Status |
|---|--------|--------|
| 1 | Command list update strategy | Resolved: dynamic — startup + periodic (command_discovery_interval_sec); mark unavailable when server down |
| 2 | allow_by_default + allowed_commands | Resolved: intersection when allowed_commands non-empty |
| 3 | last_n_messages config | Resolved: param name, units (count), default |
| 4 | Standards / session rules source | Resolved: passed at session create, stored in local Redis, updatable; schema reflects |
| 5 | Session model optional at create | Resolved: optional at create; required before context build |
| 6 | Session update (set model) command | Resolved: add SessionUpdateCommand in step 13 |
| 7 | Display name uniqueness | Resolved: alias unique per (session, model); duplicate → fallback |
| 8 | Model → context window size and representation | Resolved: §2.5 (Ollama + Google: context size source, representation format, registry lookup) |
| 9 | Redis layout | Implementation-phase; document in impl |
| 9a | Message id as primary key | Resolved: uuid primary key; by uuid full message assemblable; indices secondary |
| 9b | chunk_metadata_adapter (Redis field names) | Resolved: uuid, created_at, source, body, session_id; sync with corporate DB |
| 9c | External data sources, Database, DatabaseManager | Resolved: §4.4e (priority), §4.4f (Database, DatabaseManager; chunk_metadata_adapter as glue) |
| 9d | Redis: described structure (schema); embedding not in Redis | Resolved: §3.2a (schema); §3.3/3.4 (no embedding in Redis; vectors in DB table + index) |
| 9e | Chunk store: only chunk_id; vectors in DB; reindex | Resolved: §3.5.4, §4.2a, §4.2b (chunk_id + Lua resolution; vector table; reindex) |
| 9f | Soft delete; no FAISS remove; filter + reindex | Resolved: is_deleted in DB; filter before sort; reindex from non-deleted only |
| 10 | Chunker and vectorizer | Resolved: chunker chunks+vectorizes (calls vectorizer internally); embed client for query embedding only |
| 10a | Redis ↔ FAISS/index and search methods | Resolved: §4.2a (worker, index update), §4.2b (semantic + BM25 search) |
| 10b | ContextBuilder message source | Resolved: MessageStore abstraction; default RedisMessageStore |
| 11 | RelevanceSlotBuilder full vs stub | Resolved: first impl = fixed-order; config flag for unified later |
| 12 | Session-init name and response | Resolved: JSON — command name, session_id (response), parameters (session record fields) |
| 13 | Config generator and validator | Resolved: §6.4; adapter first, project overlay; step 01 deliverable includes both; steps 05, 09, 10, 12 extend both when adding config |

---

## 14. Post-change consistency check

After adding message_id as primary key, chunker (chunks+vectorizes) and embed client (query only), RelevanceSlotBuilder first impl = fixed-order, RepresentationRegistry population at startup, chat flow integration checklist, and external data sources (Database, DatabaseManager, priority), the following was verified and fixed:

- **Main plan Object model table:** SessionUpdateCommand was missing; added row for SessionUpdateCommand (session_id, optional model, allowed_commands, forbidden_commands).
- **step_10:** Wording "embedding and chunker" → "chunker (chunk+vectorize) and embed client (query)" for alignment with §4.2a.
- **14 §10 / §10a:** Chunker does chunking and vectorization; embed client used at query time for query embedding. Main plan §4.2, §4.2a, §4.2b updated.
- **External data sources:** Main plan §4.4e (priority), §4.4f (Database, DatabaseManager; chunk_metadata_adapter); §4.6 summary and §4.5 config mention external sources; 00_objects_and_diagrams and step_11 reference Database/DatabaseManager and optional integration.
- **Vector table and soft delete (9f):** §3.5.4 and §4.2a: vector table schema (chunk_id UUID4, vector, vector_index_id from FAISS add, is_deleted); add flow (DB first → FAISS add → store ID); soft delete (mark only; filter in all queries); no removal from FAISS; reindex from non-deleted only.

No remaining ambiguities introduced by these changes. #10b closed in step_10 implementation (MessageStore + RedisMessageStore).
