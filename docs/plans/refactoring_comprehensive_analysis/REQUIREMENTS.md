<!--
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
-->

# Requirements — provider abstraction & search

Clarified 2026-05-01. Source: architecture review session.
All items below are normative for the refactoring plan.

---

## 1. Provider layer

### 1.1 Class hierarchy

One abstract base class, concrete subclasses per provider family:

```
BaseProviderClient (ABC)          # provider_client_base.py
  ├── MwpsProviderClient        # mwps_provider_client.py
  ├── OpenAIProviderClient        # openai_provider_client.py  (OpenAI-compatible REST)
  │     used also for: xai, deepseek (same API shape, different base_url + key)
  ├── AnthropicProviderClient     # anthropic_provider_client.py  (Messages API)
  ├── GoogleProviderClient        # google_provider_client.py  (Gemini API only,
  │                               #   NOT Vertex AI; generativelanguage.googleapis.com)
  └── DeepSeekProviderClient      # deepseek_provider_client.py  (OpenAI-compatible,
                                  #   but separate class if behaviour diverges)
```

**Rule:** OpenAI-compatible providers (openai, xai, deepseek) may share a base
implementation `OpenAICompatibleProviderClient(BaseProviderClient)` that is
parameterised by `base_url` and `api_key`. Each gets its own thin subclass that
sets defaults and overrides only what differs. Google Gemini is NOT
OpenAI-compatible and MUST be a separate class.

### 1.2 Required providers

All six canonical providers from `provider_client_config_standard.md` §2 must
have a concrete implementation:

| Provider name | Class | API style |
|---|---|---|
| `mwps` | MwpsProviderClient | Model Workplace Server HTTP (`/api/chat`, `/api/embed`) |
| `openai` | OpenAIProviderClient | OpenAI REST (`/v1/chat/completions`) |
| `anthropic` | AnthropicProviderClient | Anthropic Messages API |
| `google` | GoogleProviderClient | Gemini API (`generativelanguage.googleapis.com`) |
| `xai` | XAIProviderClient (extends OpenAI-compat) | OpenAI-compatible |
| `deepseek` | DeepSeekProviderClient (extends OpenAI-compat) | OpenAI-compatible |

### 1.3 Contract compliance (fixing P1–P6 from architecture review)

- **P1 fix:** Remove all direct `MwpsRepresentation()` instantiations from
  `chat_flow.py`, `mwps_chat_command.py`, `get_model_context_command.py`.
  All representation lookup must go through `RepresentationRegistry`.
- **P2 fix:** Implement `provider_registry.get_client()` for all six providers.
  Remove `NOT IMPLEMENTED` from `commercial_chat_client.py`.
- **P3 fix:** `MwpsServerChatCommand` and `MwpsServerEmbedCommand` must be
  removed or rerouted through `BaseProviderClient`. Direct HTTP to Model Workplace Server API
  is forbidden outside the provider client.
- **P4:** Two vectorization paths are intentional — see §3.
- **P5 fix:** `tools.py::get_mwps_tools()` must delegate tool serialization
  to `ContextRepresentation.serialize_tools()` via the registry. The function
  must be renamed `get_tools_for_model(model_id)` and become provider-agnostic.
- **P6 fix:** `WorkstationConfig` flat Model Workplace Server fields (`mwps_url`,
  `mwps_model`) must be replaced by the normalized `provider_clients`
  structure from `provider_client_config_standard.md`.

---

## 2. Provider configuration

### 2.1 Structure (per standard §1)

Each provider has an **optional top-level section**. When the provider is
active (referenced by `default_provider` or used in a session), its section
becomes **mandatory** and must pass full validation before startup.

```yaml
provider_clients:
  default_provider: mwps        # must reference an existing key below
  providers:

    mwps:
      transport:
        base_url: "http://localhost:11434"
        request_timeout_seconds: 120
      features:
        supports_stream: true
        supports_tools: true
        supports_embeddings: true
        default_model: "llama3.2"
        embed_model: "nomic-embed-text"
      limits:
        max_tokens: 8192
        max_context_tokens: 131072

    openai:
      transport:
        base_url: "https://api.openai.com"
        request_timeout_seconds: 60
      auth:
        api_key: "${OPENAI_API_KEY}"     # env-var interpolation required
      features:
        supports_stream: true
        supports_tools: true
        supports_embeddings: true
        default_model: "gpt-4o"
        embed_model: "text-embedding-3-small"
      limits:
        max_tokens: 4096
        max_context_tokens: 128000

    anthropic:
      transport:
        base_url: "https://api.anthropic.com"
        request_timeout_seconds: 120
      auth:
        api_key: "${ANTHROPIC_API_KEY}"
      features:
        supports_stream: true
        supports_tools: true
        supports_embeddings: false       # Anthropic has no embed API
        default_model: "claude-opus-4-6"
        anthropic_version: "2023-06-01"  # required header
      limits:
        max_tokens: 4096
        max_context_tokens: 200000

    google:
      transport:
        base_url: "https://generativelanguage.googleapis.com"
        request_timeout_seconds: 120
        api_version: "v1beta"            # Gemini API version prefix
      auth:
        api_key: "${GOOGLE_API_KEY}"     # or service account JSON path
        # service_account_json: "${GOOGLE_APPLICATION_CREDENTIALS}"
      features:
        supports_stream: true
        supports_tools: true
        supports_embeddings: true
        default_model: "gemini-2.0-flash"  # chat model
        embed_model: "text-embedding-004"  # embed model
        safety_settings: []                # optional: list of {category, threshold}
      limits:
        max_tokens: 8192
        max_context_tokens: 1000000

    xai:
      transport:
        base_url: "https://api.x.ai"
        request_timeout_seconds: 60
      auth:
        api_key: "${XAI_API_KEY}"
      features:
        supports_stream: true
        supports_tools: true
        supports_embeddings: false
        default_model: "grok-3"
      limits:
        max_tokens: 4096
        max_context_tokens: 131072

    deepseek:
      transport:
        base_url: "https://api.deepseek.com"
        request_timeout_seconds: 120
      auth:
        api_key: "${DEEPSEEK_API_KEY}"
      features:
        supports_stream: true
        supports_tools: true
        supports_embeddings: false
        default_model: "deepseek-chat"
      limits:
        max_tokens: 4096
        max_context_tokens: 64000
```

### 2.2 Validation rules (extends standard §3)

- **V-PROV-1:** If a provider section is present, `transport.base_url` is mandatory.
- **V-PROV-2:** If `transport.base_url` starts with `https://`, TLS section may
  be absent (default system CA used); must not explicitly disable TLS.
- **V-PROV-3:** If `features.supports_embeddings: true`, `features.embed_model`
  must be set.
- **V-PROV-4:** For providers requiring auth (openai, anthropic, google, xai,
  deepseek): `auth.api_key` must be non-empty. Env-var references
  (`${VAR}`) are resolved at validation time; missing env var = startup failure.
- **V-PROV-5:** `google` provider: if both `api_key` and
  `service_account_json` are set, startup must fail (ambiguous auth).
- **V-PROV-6:** `google` provider: `features.safety_settings` entries must each
  have `category` and `threshold` fields.

### 2.3 Config migration (WorkstationConfig)

Current flat fields (`mwps_url`, `mwps_model`) must be replaced by the
normalized structure above. Migration steps:
1. Parse new `provider_clients` section in `load_config()`.
2. Build `ProviderClientConfig` dataclass from parsed section.
3. Remove `mwps_url`, `mwps_model`, `mwps_embed_model` from
   `WorkstationConfig`.
4. `provider_registry.get_client(provider_name, config)` reads from
   `config.provider_clients.providers[provider_name]`.

---

## 3. Vectorization paths (two intentional paths)

Two paths exist by design with distinct responsibilities:

### 3.1 Path A — SVO chunker client (indexing)

**Class:** `VectorizationClient` → `EmbedProxyClient`
**When used:** indexing new content into the knowledge base.
**What it does:** calls `svo-chunker-prod` service → returns `SemanticChunk`
objects (from `chunk-metadata-adapter` package) containing:
- `text` — chunk text
- `embedding_vector` — dense vector
- `bm25_tokens` — sparse token list
- full chunk metadata (uuid, sha256, created_at, type, role, tags, etc.)

**Output stored in:** Redis (primary store for all chunk data and vectors)
plus FAISS index updated with new vector_id.

**NOT interchangeable with Path B.** Path A produces chunks with full
metadata; Path B does not chunk — it only vectorizes a query string.

### 3.2 Path B — embed-client (query vectorization)

**Class:** `VectorizationClient` → `DirectEmbedVectorizationClient`
**When used:** at search time, to vectorize the user's query string.
**What it does:** calls `embed-service` directly → returns a single dense
vector. No chunking, no metadata, no BM25 tokens.

**Used by:** `search` command to build the query vector before ANN lookup.

### 3.3 Vector storage architecture

```
Redis (primary store)
  key: chunk:{uuid}  →  SemanticChunk (full data incl. embedding_vector)

FAISS index (ANN lookup only)
  vector_id (int)  →  used as ANN result, then resolved via lookup table

Lookup table (Redis hash)
  key: faiss_id_map  →  {faiss_vector_id: chunk_uuid}
```

**Invariant:** FAISS is a pure index — it holds no data. Every FAISS
`vector_id` maps to a `chunk_uuid` in the lookup table, which maps to a
full `SemanticChunk` in Redis. FAISS can be fully rebuilt from Redis at any
time (e.g. on startup or `rebuild_faiss`).

---

## 4. Search command

### 4.1 Single `search` command with options

One MCP command `search` replaces ad-hoc calls to `semantic_search`.
Default mode: semantic (dense vector ANN via FAISS → resolve via lookup →
fetch from Redis).

```
search(
  query: str,                       # natural language or keyword query
  mode: "semantic" | "bm25" | "hybrid" = "semantic",
  filter_expr: str | None = None,   # ChunkQuery DSL (see §4.2)
  limit: int = 10,
  min_score: float = 0.0,
  project_id: str | None = None,    # scope to one project
)
```

### 4.2 Query language for filtering

Filtering on `SemanticChunk` metadata fields uses `ChunkQuery` from
`chunk-metadata-adapter`:
- Parser: `FilterParser` → AST
- Executor: `FilterExecutor` — evaluates AST against chunk metadata dict
- Validator: `QueryValidator` — security + complexity check before execution

**Example `filter_expr` values:**
```
type = 'CodeBlock' AND quality_score >= 0.8
tags intersects ['auth', 'security'] AND NOT is_deleted
year >= 2025 AND (role = 'canon' OR role = 'clarification')
```

Filter is applied **after** ANN retrieval (post-filter), not inside FAISS.
For high-selectivity filters, BM25 or hybrid mode is recommended.

### 4.3 Search modes

| Mode | How | When |
|------|-----|------|
| `semantic` | embed query → FAISS ANN → lookup → fetch from Redis → apply filter | default; best for natural language |
| `bm25` | tokenize query → BM25 match against `bm25_tokens` in Redis → apply filter | keyword-heavy, exact terms |
| `hybrid` | run both → merge via `HybridSearchHelper` (WEIGHTED_SUM default) → apply filter | best recall |

---

## 5. ContextRepresentation per provider

Each provider requires its own `ContextRepresentation` subclass because
message and tool formats differ:

| Provider | Representation class | Notes |
|---|---|---|
| `mwps` | `MwpsRepresentation` | already implemented |
| `openai` | `OpenAIRepresentation` | tool calls: `{type: function, function: {name, arguments}}` |
| `anthropic` | `AnthropicRepresentation` | tool use: `{type: tool_use, name, input}` |
| `google` | `GeminiRepresentation` | function calling: `{functionCall: {name, args}}` |
| `xai` | `XAIRepresentation` | OpenAI-compatible → may extend `OpenAIRepresentation` |
| `deepseek` | `DeepSeekRepresentation` | OpenAI-compatible → may extend `OpenAIRepresentation` |

All registered in `RepresentationRegistry` by `model_id` (or by
`provider_name` fallback when model_id is not matched).

---

## 6. Open questions at time of writing

None — all clarifications received 2026-05-01.
