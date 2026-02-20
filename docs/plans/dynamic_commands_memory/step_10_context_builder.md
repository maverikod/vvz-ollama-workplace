# Step 10: Context builder (trimming and slots)

**Author:** Vasiliy Zdanovskiy  
**Email:** vasilyvz@gmail.com  

**Scope:** Build the model context for a request: load session, get representation, compute effective limit, load messages, apply order (standards, session rules, N messages, relevance slot), trim, fill slots, serialize via representation. One step = one file (this doc).

## Goal

- **ContextBuilder** builds the full context for a chat request: load session by session_id; get representation for session.model; compute effective_limit = min(session model window, config max_context_tokens); load messages from Redis/semantic store for session_id; apply order (standards → session rules → last N messages → relevance slot); trim to fit effective_limit; fill relevance slot (unified or fixed order); serialize messages (and optionally tools) via ContextRepresentation.
- **TrimmedContext** (or similar): result structure with ordered segments and token/size info.
- If remainder < min_semantic_tokens after placing standards, rules, and N messages: log error and abort (or return clear error to client).

## Objects

- **ContextBuilder:** build(session_id, current_message, config) -> (TrimmedContext, serialized for API). Uses SessionStore, RepresentationRegistry, message store, RelevanceSlotBuilder, optional DocumentationSlotBuilder.
- **TrimmedContext:** Ordered segments (standards, session_rules, last_n_messages, relevance_slot_content); optional token counts.
- **RelevanceSlotBuilder:** Fills the relevance slot: either unified (session chunks + doc chunks ranked by vector distance to current message) or fixed order (semantic then doc). Depends on DocumentationSource when doc chunks are used (step 11). **Scope for first implementation:** use **stub/fixed-order only** (semantic slot then documentation block); add config flag `relevance_slot_mode` (e.g. `fixed_order` | `unified_by_relevance`) and implement full unified ranking in a later phase when chunker (chunk+vectorize) and embed client (query embedding) are available. **When implementing semantic/BM25 search path:** search returns **chunk_ids** (and scores); body, session_id resolved by **lookup** (chunk_id → message_id → Redis; e.g. Redis Lua). **Filter out** chunks marked **is_deleted** in the vector table (main plan §4.2b, §3.5.4) before sort/limit so deleted chunks never appear. Reindex builds the vector index only from non-deleted rows.

## Inputs / outputs

- **Input:** session_id, current_message (and optionally full message list if already in memory), config (max_context_tokens, min_semantic_tokens, min_documentation_tokens, **last_n_messages**, relevance_slot_mode). **last_n_messages**: integer, number of **messages** (not tokens) to always include in context; default e.g. 10 or 20. Token count of these N messages is subtracted from remainder when computing slot size.
- **Output:** TrimmedContext and the payload ready for the model API (after representation.serialize_messages). Tool list is built separately (step 06) and serialized via representation.

## Acceptance criteria

- Effective limit is always min(session model window, config max_context_tokens). Session.model is required.
- Order of segments is respected. **last_n_messages** (config) defines how many recent messages are always included (by message count); relevance slot is filled within remainder.
- When remainder < min_semantic_tokens, build fails with clear error and no partial send.

## References

- Main plan: [§4.2 Flow](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#42-flow), [§4.2a Redis, vector table, vector index, index update](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#42a-redis-vector-table-db-vector-index-eg-faiss-and-index-update), [§4.2b Search methods: semantic and BM25](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#42b-search-methods-semantic-and-bm25), [§4.3 Context order](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#43-context-order-priorities), [§4.4 Context size and semantic slot](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#44-context-size-and-semantic-slot), [§3.5.4 Vector store, chunk resolution, soft delete](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#354-vector-store-db-table-and-vector-index-chunk-resolution-by-id-soft-delete).
- Objects and diagrams: [00_objects_and_diagrams.md](00_objects_and_diagrams.md) (ContextBuilder, TrimmedContext, RelevanceSlotBuilder), [diagram: context build and representation](00_objects_and_diagrams.md#4-diagram-context-build-and-representation).
- Prev: [step_09_redis_message_writer.md](step_09_redis_message_writer.md). Next: [step_11_documentation_source.md](step_11_documentation_source.md). Uses steps 05, 07, 09; step 11 optional.

## Success metrics

- **Step-specific:** effective_limit = min(session model window, config max_context_tokens); segment order standards → session rules → N messages → relevance slot; remainder < min_semantic_tokens ⇒ build fails with clear error; N messages always included.
- **Standard verification:** No incomplete code, TODO, ellipsis, or syntax issues; no `pass` outside exceptions; no `NotImplemented` outside abstract methods; no deviations from [RULES](../../RULES.md) or plan. After code: `code_mapper -r src`; `mypy src`, `flake8 src tests`, `black src tests` (fix all).

## Comparative analysis vs existing code

| Aspect | Existing | To change | To add |
|--------|----------|-----------|--------|
| Context | chat_flow passes messages and model to OLLAMA; no trimming/slots | — | ContextBuilder: load session, get representation, effective_limit, load messages, order segments, trim, fill relevance slot, serialize via representation |
| Session | No session yet (step 05) | — | Uses SessionStore.get(session_id); session.model for limit and representation |
| Limits | config has ollama_timeout, max_tool_rounds | Extend config for max_context_tokens, min_semantic_tokens, min_documentation_tokens, last_n_messages | — |
| **Config generator / validator** | — | — | When adding context config: update generator overlay and `validate_project_config` per main plan §6.4 (adapter first, project on top). |

## Dependencies

- Steps 05 (SessionStore), 07 (RepresentationRegistry), 09 (message source; context builder reads from store/Redis or a service that aggregates messages). Step 11 (DocumentationSource) optional for this step if relevance slot is implemented without doc first. **Semantic memory path (when implemented):** Vector table (DB) and vector index (e.g. FAISS) per §4.2a; SemanticMemorySearch returns chunk_ids, resolution via lookup (Redis/Redis Lua); filter by is_deleted in vector table (§4.2b, §3.5.4).

## Deliverable

- ContextBuilder, TrimmedContext; RelevanceSlotBuilder in **fixed-order** variant (semantic then doc) for first implementation; config flag for future unified mode. Integration with session store and representation registry. When adding semantic/BM25 search: respect chunk_id-only storage, resolution by lookup, and **filter deleted** (is_deleted) before building result set. Unit tests with mocked store and representation.
