# STEP-S2 — FAISS↔Redis lookup table

**Concern:** `vectorization_client.py`, Redis schema, FAISS index management
**Severity:** 🔴 High
**Depends on:** STEP-S1 (search command needs lookup at runtime)

---

## Architecture (from REQUIREMENTS §3.3)

```
Redis (primary store)
  key: chunk:{chunk_uuid}    -> SemanticChunk JSON (full data + embedding_vector)

FAISS (ANN index only)
  vector_id (int, 0-based)   -> used as ANN result ID

Lookup table (Redis hash)
  key:   faiss_id_map:{project_id}
  field: str(faiss_vector_id)
  value: chunk_uuid
```

**Invariant:** Every FAISS vector_id has a corresponding entry in
`faiss_id_map`. FAISS can be fully rebuilt from Redis at any time.

## Current state

`EmbedProxyClient` (Path A, SVO chunker) stores chunks in Redis but
does NOT maintain a `faiss_id_map` hash. FAISS index is built separately
(via `rebuild_faiss` in code-analysis-server) without a stable
vector_id↔uuid mapping accessible to mwps.

## Task

### S2a. Write faiss_id_map on indexing

When `EmbedProxyClient` stores a new chunk:
1. Chunk is stored: `Redis.set(f"chunk:{uuid}", chunk.model_dump_json())`
2. Get FAISS vector_id assigned to this chunk (returned by indexing pipeline)
3. Store mapping: `Redis.hset(f"faiss_id_map:{project_id}", faiss_vector_id, uuid)`

If the indexing pipeline does not return vector_id yet, add it:
- Option A: FAISS index built in append order; vector_id = current index size before add
- Option B: SVO chunker returns vector_id in response — check `SemanticChunk` schema

### S2b. Resolve function

```python
def resolve_faiss_ids(
    redis_client,
    project_id: str,
    faiss_ids: list[int],
) -> dict[int, str]:
    """Return {faiss_id: chunk_uuid} for given ids.
    Missing ids logged as warnings (stale index).
    """
    map_key = f"faiss_id_map:{project_id}"
    result = {}
    for fid in faiss_ids:
        uuid = redis_client.hget(map_key, str(fid))
        if uuid:
            result[fid] = uuid.decode()
        else:
            logger.warning("faiss_id %d has no chunk_uuid mapping", fid)
    return result
```

### S2c. Rebuild support

`rebuild_faiss_from_redis(project_id)` function:
1. Scan all `chunk:{uuid}` keys for project
2. Extract `embedding_vector` from each
3. Build new FAISS index in insertion order
4. Rebuild `faiss_id_map` hash (new_vector_id → uuid)
5. Atomic swap: write new index file, update Redis hash

This ensures FAISS + lookup table are always consistent.

### S2d. Stale entry cleanup

When a chunk is deleted from Redis:
- Remove `faiss_id_map` entry
- Mark FAISS slot as deleted (or trigger rebuild if fragmentation > threshold)

## Redis key schema summary

| Key pattern | Type | Content |
|-------------|------|---------|
| `chunk:{uuid}` | string | `SemanticChunk` JSON |
| `faiss_id_map:{project_id}` | hash | `{str(faiss_id): chunk_uuid}` |
| `chunk_index:{project_id}` | set | All chunk_uuids for a project (for BM25 scan) |

## Acceptance criteria

- [ ] `faiss_id_map:{project_id}` populated on every new chunk indexed
- [ ] `resolve_faiss_ids()` returns correct uuid for each faiss_id
- [ ] Missing faiss_id logged, not raised (graceful degradation)
- [ ] `rebuild_faiss_from_redis()` produces consistent index + map
- [ ] Chunk deletion removes faiss_id_map entry
- [ ] Unit tests: write chunk, verify map entry; resolve; rebuild
- [ ] `lint_code` + `type_check_code` pass
