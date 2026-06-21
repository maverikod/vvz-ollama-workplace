# STEP-S1 — search command (new file)

**File:** `src/ollama_workstation/commands/search_command.py` (new)
**Severity:** 🔴 High
**Depends on:** STEP-I1 (embed via OpenAI-compat or Ollama), STEP-P1, STEP-S2

---

## Purpose

Single MCP command `search` replacing ad-hoc semantic_search calls.
Provides semantic (dense ANN), BM25 (sparse), and hybrid modes.
Filtering via `ChunkQuery` DSL from `chunk-metadata-adapter`.

## Command schema

```python
{
  "name": "search",
  "description": "Search the knowledge base. Default: semantic ANN via FAISS + Redis.",
  "parameters": {
    "query": {"type": "string", "required": True,
              "description": "Natural language or keyword query."},
    "mode": {"type": "string", "enum": ["semantic", "bm25", "hybrid"],
             "default": "semantic"},
    "filter_expr": {"type": "string", "required": False,
                   "description": "ChunkQuery DSL filter on chunk metadata fields. "
                                  "Example: type = 'CodeBlock' AND quality_score >= 0.8"},
    "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 100},
    "min_score": {"type": "number", "default": 0.0},
    "project_id": {"type": "string", "required": False,
                  "description": "Scope search to a specific project."},
  }
}
```

## Execution flow

### Semantic mode

```
1. Validate filter_expr via QueryValidator (security + complexity)
2. Vectorize query: DirectEmbedVectorizationClient.embed(query) -> query_vector
3. FAISS ANN: faiss_index.search(query_vector, k=limit*10) -> [(faiss_id, score)]
4. Resolve: faiss_id -> chunk_uuid via lookup table (Redis hash faiss_id_map)
5. Fetch: Redis.get(f"chunk:{chunk_uuid}") -> SemanticChunk for each result
6. Filter: if filter_expr: FilterExecutor(ast).execute(chunk.metadata) for each chunk
7. Score filter: drop chunks below min_score
8. Truncate to limit
9. Return: list of {chunk_uuid, score, chunk_type, text_preview, metadata}
```

### BM25 mode

```
1. Validate filter_expr
2. Tokenize query (same tokenizer as indexing pipeline)
3. BM25 match: score each chunk in Redis by bm25_tokens overlap
   (scan chunks for project_id or use Redis FT index if available)
4. Filter + score + truncate
5. Return
```

### Hybrid mode

```
1. Run semantic + BM25 in parallel
2. Merge via HybridSearchHelper.weighted_sum(semantic_results, bm25_results,
     bm25_weight=0.3, semantic_weight=0.7)  # configurable
3. Apply filter, min_score, limit
4. Return
```

## Filter DSL integration

```python
from chunk_metadata_adapter import FilterParser, FilterExecutor, QueryValidator

def _apply_filter(chunks: list[SemanticChunk], filter_expr: str) -> list[SemanticChunk]:
    validator = QueryValidator()
    result = validator.validate(filter_expr)
    if not result.is_valid:
        raise ValidationError(f"Invalid filter_expr: {result.errors}")
    ast = FilterParser().parse(filter_expr)
    executor = FilterExecutor()
    return [c for c in chunks if executor.execute(ast, c.model_dump())]
```

Filter is **post-retrieval** (applied after ANN/BM25 fetch, before truncation).
For high-selectivity filters, the caller should use `limit*10` oversampling
or switch to BM25/hybrid.

## Return schema

```python
{
  "results": [
    {
      "chunk_uuid": str,
      "score": float,          # ANN distance or BM25 score or hybrid
      "text": str,             # SemanticChunk.text
      "chunk_type": str,       # SemanticChunk.type (CodeBlock, DocBlock, etc.)
      "source_file": str | None,
      "project_id": str | None,
      "metadata": dict,        # full SemanticChunk metadata for further filtering
    }
  ],
  "mode": str,
  "total_candidates": int,     # before filter
  "filter_applied": bool,
}
```

## Acceptance criteria

- [ ] `search(query, mode="semantic")` returns results without filter
- [ ] `filter_expr` validated via `QueryValidator` before execution
- [ ] `FilterExecutor` post-filters ANN results
- [ ] BM25 mode works independently of FAISS
- [ ] Hybrid mode runs both and merges via `HybridSearchHelper`
- [ ] `project_id` scopes results to that project
- [ ] `min_score` applied before truncation
- [ ] Invalid `filter_expr` returns error, does not crash
- [ ] `lint_code` + `type_check_code` pass
