# Context formation: rules and limits

**Author:** Vasiliy Zdanovskiy  
**Email:** vasilyvz@gmail.com  

This document describes how the model context is built (ContextBuilder) and what constraints apply. Use it to align behaviour and to verify limits without calling the model.

**Why it matters:** The model is used as the **agent's tool**. Without the right context (including semantically relevant history via the relevance slot), the model is not useful. See [techspec.md](techspec.md) §1.1.

---

## 1. Purpose

Context is the ordered list of messages (system + history + relevance slot + current user message) sent to the model for each request. It is built from:

- Config and session (limits, file paths)
- Session store (session metadata, standards, session_rules)
- Message store (conversation history)
- Optional file-based standards and rules

No model is called during context building; trimming and ordering are deterministic.

---

## 2. Parameters (config / API)

| Parameter | Meaning | Typical default |
|-----------|---------|------------------|
| **max_context_tokens** | Requested upper bound for context size (tokens). | 4096 |
| **last_n_messages** | Maximum number of history messages to include (by count). | 10 |
| **min_semantic_tokens** | Reserved space for semantic/relevance slot. | 256 |
| **min_documentation_tokens** | Reserved space for documentation slot. | 0 |
| **model_context_tokens** | Model's context window (builder init). From config or representation. | 4096 |
| **standards_file_path** | Optional path: file content is prepended to standards. | "" |
| **rules_file_path** | Optional path: file content is prepended to session rules. | "" |

Session can also define `standards` and `session_rules` (lists of strings), merged with file content as below.

---

## 3. Effective limit and remainder

- **effective_limit** = `min(model_context_tokens, max(1, max_context_tokens))`  
  So the cap is the stricter of: the model's window and the requested `max_context_tokens`.

- **remainder** = `effective_limit - min_semantic_tokens - min_documentation_tokens`

- **Constraint:** `remainder >= 0`.  
  If `remainder < 0`, **ContextBuilder.build()** raises **ContextBuilderError** with a message like "Remainder < min_semantic_tokens; reduce last_n or increase limit". No request is sent to the model.

So: if you set `max_context_tokens` (or the model window) too small relative to `min_semantic_tokens + min_documentation_tokens`, the build fails before any serialization.

---

## 4. Segment order

The context is built as four segments, concatenated in this order:

1. **Standards**  
   - If `standards_file_path` is set and the file exists, its content is loaded and added as one system block, then  
   - Session `standards` (each item as a system block).

2. **Session rules**  
   - If `rules_file_path` is set and the file exists, its content is loaded and added as one system block, then  
   - Session `session_rules` (each item as a system block).

3. **Last N messages**  
   - From the message store for the session, only the **last `last_n_messages`** messages (by count).  
   - Each message is normalized to `role` and `content` (and optional fields like `tool_calls`).  
   - No token-level trimming is applied inside this segment; only the count is capped.

4. **Relevance slot**  
   - Filled by `RelevanceSlotBuilder.fill_slot(current_message, session_id, last_n_messages)` (async).  
   - When a **vectorization client** (embed-client via proxy) is configured: messages are **vectorized** and ranked by **vector similarity** (cosine) to the current message. Otherwise: ranked by word overlap. All relevant blocks (older history + optional documentation source) are sorted by that score. No token trimming inside the slot.  
   - Trimming by token limit is applied **after** the full context is built (see below).

5. **Trim after context creation**  
   - After concatenating segments and serializing, `trim_messages_to_token_limit(serialized, effective_limit)` is applied: messages are dropped from the **start** until estimated total tokens (chars ÷ 4) ≤ `effective_limit`. The tail (most recent) is kept.

After that, the **current user message** is appended by the caller (not inside ContextBuilder). So the full payload is:  
`trimmed_serialized + [current_message]`.

---

## 5. Trim after context creation

- After serialization, **trim_messages_to_token_limit(serialized, effective_limit)** is applied: messages are dropped from the **start** until estimated total tokens (content chars ÷ 4) ≤ `effective_limit`. The tail is kept when possible.
- Standards and session_rules may be dropped if at the start when over limit.

So the **only hard numeric constraint** in the builder is:  
`effective_limit - min_semantic_tokens - min_documentation_tokens >= 0`.  
Everything else is "include up to N messages" and "append these blocks". Overflow beyond the model window is not enforced in code and would be the responsibility of the API or a future token-counting trim step.

---

## 6. Summary of limits (for verification)

| Rule | How to verify without model |
|------|-----------------------------|
| effective_limit = min(model_context_tokens, max_context_tokens) | Use different builder init and build() params; indirect via remainder. |
| remainder = effective_limit - min_semantic - min_documentation | Compute from params; build must not raise when remainder >= 0. |
| remainder < 0 → ContextBuilderError | Call build() with e.g. max_context_tokens=200, min_semantic_tokens=256 → expect raise. |
| last_n_messages caps history count | Store 5 messages, last_n_messages=2 → trimmed.last_n_messages has length 2. |
| Order: standards → session_rules → last_n → relevance_slot | Check serialized message order (and TrimmedContext fields). |
| Session not found → ContextBuilderError | build(unknown_session_id, ...) → expect raise. |
| Session model not set → ContextBuilderError | Session with model=None and no model_override → expect raise. |
| File standards/rules prepended when path set | Use tmp files; assert serialized[0] etc. match file then session content. |

---

## 7. All providers receive the same full context

**Guarantee:** In the **mwps_chat** path, **every** model (Model Workplace Server and all commercial providers: Google, OpenAI, Anthropic, xAI, DeepSeek, OpenRouter) receives the **same** context: (1) **Rules and standards** — file-based plus session standards and session_rules, as system messages; (2) **Tools** — the effective tool list in the request body; (3) **History** — last N messages from the message store; (4) **Semantic augmentation** — relevance slot (RelevanceSlotBuilder). Context is built once in MwpsChatCommand and the same `history` and `tools` are passed to run_chat_flow; both Model Workplace Server and commercial endpoints receive that same payload (commercial via _mwps_to_openai_messages, which preserves roles). **direct_chat** does not use context; use **mwps_chat** for full context with any provider.

---

## 8. Where it is used

- **mwps_chat** (MwpsChatCommand): builds context with config's max_context_tokens, last_n_messages, min_semantic_tokens, min_documentation_tokens; on ContextBuilderError falls back to all messages from store + current (no trim/slots).
- **get_model_context** (GetModelContextCommand): same build; on error returns error result instead of fallback.
- Both use the same ContextBuilder contract; verification scripts can use in-memory session and message stores and no MWPS/Redis to assert these rules.

**Script:** `scripts/verify_context_limits.py` runs the above checks without a model or Redis (in-memory stores only). Run from project root with `.venv` activated: `python scripts/verify_context_limits.py`.

---

## 9. Token usage logging (for effect evaluation)

To evaluate context size and cost (e.g. before/after minimize_context or config changes), the following is logged:

- **chat_flow context_size** (each round): `round`, `messages`, `chars`, `tokens_est` (content length ÷ 4). Logged before sending the request to MWPS.
- **chat_flow token_usage** (each round after response): `round`, `prompt_eval`, `eval`, `total_prompt`, `total_eval` from the MWPS response (`prompt_eval_count`, `eval_count`). Accumulated across tool-call rounds.
- **chat_flow done**: `duration_sec`, `rounds`, `total_prompt`, `total_eval`, `total` (prompt + eval tokens).
- **mwps_chat context_build** (session mode): `duration_sec`, `history_len`, `content_chars`, `tokens_est` for the built context.

Use these log lines to compare token usage across runs or settings.

---

## 10. Verifying semantic mixing (relevance slot)

**Goal:** Confirm that older messages are added to context by **semantic relevance** to the current message (not only by chronological order). The relevance slot is filled by `RelevanceSlotBuilder.fill_slot()`: when a vectorization client is set, older messages (excluding the last N) are ranked by **cosine similarity** of their embeddings to the current user message and appended after `last_n_messages` in the context.

**Test scenario (manual, via MCP or adapter API):**

1. **Create a session** (e.g. `session_init` with model `qwen2.5-coder:1.5b`).

2. **Run a coherent dialogue** (at least 25 exchanges) with **clearly separated topics** so that "old" content is outside the `last_n_messages` window (e.g. if `last_n_messages=10`, use at least 6–7 full turns on other topics before the callback):
   - **Block A (turns 1–5):** Introduce a topic with unique wording.
   - **Block B (turns 6–12):** Different topic.
   - **Block C (turns 13–18):** Another topic.
   - **Block D (turns 19–20):** Short return to first topic.

3. **Semantic callback turn:** Ask a question that is **semantically close** to Block A but **does not repeat** its exact words.

4. **Check context:** Call `get_model_context(session_id, content=<the semantic question>)`. In the returned `messages` list: **Expected:** At least one **older** message from Block A appears. Non-chronological order indicates semantic mixing.

5. **Repeat** the context check after a few more turns.

**Requirements:** Session store and message store (e.g. Redis) must persist history; vectorization client (embedding server) must be configured and reachable so that `RelevanceSlotBuilder` uses vector similarity rather than only word overlap.
