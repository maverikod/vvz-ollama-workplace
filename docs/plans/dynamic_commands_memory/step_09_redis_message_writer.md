# Step 09: Redis message stream writer

**Author:** Vasiliy Zdanovskiy  
**Email:** vasilyvz@gmail.com  

**Scope:** Write every chat message (user, model, tool) to Redis with uuid (primary key), created_at, source, body, session_id. Field names aligned with **chunk_metadata_adapter** (SemanticChunk) for transmission and sync with the corporate DB. One step = one file (this doc).

## Goal

- Persist the **message stream** into Redis: each message is written with metadata (main plan §3). Redis is used for **transmission and synchronization** with the permanent corporate database; we use only the fields we need; names match **chunk_metadata_adapter** (SemanticChunk).
- **Primary key:** **uuid** (UUID4). Same name as SemanticChunk.uuid; this value is the message id (when chunks are built from this message, chunk.source_id = this uuid). By uuid the full message must be retrievable. Indices (e.g. by session_id) are for listing/filtering.
- **Recorded fields:** uuid (primary key), created_at (ISO 8601 with timezone), source (user | model | tool | external_agent), body (content), session_id (UUID4, mandatory). Same names as SemanticChunk where applicable; session_id is our addition for scope. **No embedding** in Redis — vectors are stored in the **vector table (DB)** and in the vector index (e.g. FAISS) built from it (main plan §3.5.4). chunk_metadata_adapter uses include_embedding=False for Redis.
- **Schema:** The structure of the message store (field names, types, purpose) must be **described explicitly** (main plan §3.2a), analogous to Database capability, so clients and corporate DB share the same contract.
- Writer is called from the chat flow (or middleware) on each message; no dependency on context builder or representation.

## Objects

- **MessageSource:** Enum or constants: user, model, tool, external_agent.
- **RedisMessageRecord:** Value object: uuid (primary key), created_at, source, body, session_id. Aligned with chunk_metadata_adapter (SemanticChunk); writer generates or accepts uuid; storage must allow get-by-uuid to reassemble the full message.
- **MessageStreamWriter:** write(record: RedisMessageRecord). Connects to Redis (config: host, port, password). Stores so that message is keyed by uuid (e.g. key = `message:{uuid}`); indices by session_id for listing are secondary. Key layout and retention to be defined in implementation.

## Inputs / outputs

- **Input:** RedisMessageRecord (uuid, created_at, source, body, session_id).
- **Output:** Success or exception; no return value to caller beyond success/failure.
- Config: Redis connection (host, port, password, optional key prefix).

## Acceptance criteria

- Every write includes uuid (primary key) and session_id. Source is one of the defined values. created_at is ISO 8601 with timezone.
- Storage design: given uuid, the full message (created_at, source, body, session_id) can be retrieved; indices (e.g. by session) are for listing only.
- If Redis is unavailable, behaviour is defined (e.g. log and skip, or fail request); no silent drop of data without logging.
- Key layout and structure (primary key by uuid, secondary indices, TTL) documented for implementation phase. **Schema description** (field names, types, purpose) documented explicitly (§3.2a).

## References

- Main plan: [§3 Memory — Redis message stream](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#3-memory--redis-message-stream), [§3.2 Recorded fields](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#32-recorded-fields), [§3.2a Described structure (schema)](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#32a-described-structure-schema-of-the-message-store), [§3.5 Schema and structure of data stores](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#35-schema-and-structure-of-data-stores-reference) (Redis message store §3.5.1); §3.3 (no embedding in Redis; vectors in vector table + index).
- Objects and diagrams: [00_objects_and_diagrams.md](00_objects_and_diagrams.md) (MessageSource, RedisMessageRecord, MessageStreamWriter), [diagram: message stream to Redis](00_objects_and_diagrams.md#6-diagram-message-stream-to-redis).
- Prev: [step_08_ollama_representation.md](step_08_ollama_representation.md). Next: [step_10_context_builder.md](step_10_context_builder.md). Chat flow calls the writer.

## Success metrics

- **Step-specific:** Every write has uuid (primary key) and session_id; source is one of user|model|tool|external_agent; created_at ISO 8601; get-by-uuid retrieves full message; Redis unavailable behaviour defined and logged; key layout (primary by uuid, indices, TTL) documented; field names aligned with chunk_metadata_adapter.
- **Standard verification:** No incomplete code, TODO, ellipsis, or syntax issues; no `pass` outside exceptions; no `NotImplemented` outside abstract methods; no deviations from [RULES](../../RULES.md) or plan. After code: `code_mapper -r src`; `mypy src`, `flake8 src tests`, `black src tests` (fix all).

## Comparative analysis vs existing code

| Aspect | Existing | To change | To add |
|--------|----------|-----------|--------|
| Persistence | No message persistence | — | MessageSource enum; RedisMessageRecord (uuid, created_at, source, body, session_id) aligned with chunk_metadata_adapter; MessageStreamWriter.write(record); storage by uuid, indices for listing; Redis config (host, port, password, prefix) |
| Chat flow | chat_flow has no writer calls | Later: after each user/model/tool message call writer with session_id | — |
| **Config generator / validator** | — | — | When adding Redis connection config: update generator overlay and `validate_project_config` per main plan §6.4 (adapter first, project on top). |

## Dependencies

- Redis client library; config. Chat flow (existing or updated) calls the writer. **chunk_metadata_adapter:** field names (uuid, created_at, source, body) aligned with SemanticChunk for sync with corporate DB; the package may be used as a reference or for validation; we do not require the full SemanticChunk model. **Chunk resolution (downstream):** The Redis message stream is the **source of truth** for resolving chunk metadata: chunk_id → message_id (source_id) → get message by uuid → body, source, session_id (main plan §3.5.4); used by semantic/BM25 search path (e.g. Redis Lua or application lookup).

## Deliverable

- MessageSource, RedisMessageRecord, MessageStreamWriter. Config schema for Redis. Schema description (field names, types, purpose) per §3.2a. Unit tests with mocked Redis or embedded Redis.
