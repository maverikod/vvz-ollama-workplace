# Unimplemented features and stubs

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com  

Report of unimplemented code, stubs, and incomplete behaviour in the OLLAMA workstation codebase (as of audit).

---

## 1. Relevance slot (semantic substitution from history)

**File:** `src/ollama_workstation/relevance_slot_builder.py`

**Status:** Implemented.

- **`RelevanceSlotBuilder.fill_slot()`** (async) gathers all relevant blocks (older history + optional DocumentationSource). When **vectorization_client** is set (embed-client via proxy): messages are **vectorized** and ranked by **vector similarity** (cosine) to the current message; otherwise fallback to word-overlap. No token trimming inside the slot.
- **Vectorization:** `VectorizationClient` / `EmbedProxyClient` in `vectorization_client.py` call embed service via proxy (`embedding_server_id`, `embedding_command`). Config: `embedding_server_id`, `embedding_command`.
- Trimming by token limit is applied **after** context creation in `ContextBuilder` via `trim_messages_to_token_limit(serialized, effective_limit)`.

---

## 2. Documentation slot not integrated into context

**Files:**  
- `src/ollama_workstation/documentation_slot_builder.py`  
- `src/ollama_workstation/context_builder.py`

**Status:** Partial.

- **`DocumentationSlotBuilder`** is implemented: uses `DocumentationSource`, returns list of content blocks (canon first, then rest). **It is never used** by `ContextBuilder`; only `RelevanceSlotBuilder` is used.
- **`DocumentationSlotBuilder.build()`** does **not** respect `remainder_tokens` (no token budget trimming). Docstring says "until budget used" but implementation ignores it.
- **Impact:** Documentation block is not part of the built context; doc slot is effectively absent.

**To implement:** (1) Integrate `DocumentationSlotBuilder` into `ContextBuilder` (e.g. optional doc slot after relevance); (2) Apply token budget in `DocumentationSlotBuilder.build()`.

---

## 3. Silent exception handling in proxy client

**File:** `src/ollama_workstation/proxy_client.py` (around lines 150–154)

**Status:** Violation of project rules.

- **`except Exception: pass`** — exceptions are swallowed with no log or re-raise.
- Project rules forbid `pass` in production; require at least logging and explicit return (e.g. `return None`).

**To implement:** Replace with `except Exception as e: logger.warning(...); return None` (or equivalent), and ensure callers handle `None`.

---

## 4. Abstract base classes (OK as designed)

The following use `raise NotImplementedError` only in **abstract** methods; concrete implementations exist and are used:

- **`SessionStore`** — `InMemorySessionStore`, `RedisSessionStore`
- **`ContextRepresentation`** — `OllamaRepresentation`
- **`MessageStore`** — in-memory and Redis implementations
- **`DocumentationSource`** — `DirectoryDocumentationSource`

No change required for "unimplemented" report; these are intentional ABCs.

---

## 5. Exception class body

**File:** `src/ollama_workstation/context_builder.py`

- **`class ContextBuilderError(Exception): pass`** — `pass` here is the standard way to define an exception with no extra behaviour. Acceptable; not a stub.

---

## Summary table

| Item                         | File(s)                          | Type        | Action                                      |
|-----------------------------|-----------------------------------|------------|---------------------------------------------|
| Relevance slot content      | relevance_slot_builder.py         | Stub       | Wire semantic search + docs; implement fill |
| Documentation slot in context | context_builder.py, documentation_slot_builder.py | Not wired / no budget | Integrate into ContextBuilder; add token budget |
| Proxy client exception      | proxy_client.py                   | Silent pass | Log and return None (or handle)             |
| ABCs / exception class      | session_store, context_representation, etc. | OK  | None                                        |

---

*Generated as an AI report; update this file when stubs are implemented or new ones are introduced.*
