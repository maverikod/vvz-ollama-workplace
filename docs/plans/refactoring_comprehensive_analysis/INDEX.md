# Refactoring Plan — Comprehensive Analysis + Provider Abstraction

**Source:** `comprehensive_analysis` run 2026-05-01 + architecture review 2026-05-01
**Scope:** `src/ollama_workstation/`, `src/model_workspace_client/`, `src/model_workspace_server/`, `scripts/`
**Requirements:** [REQUIREMENTS.md](REQUIREMENTS.md)
**Parallel map:** [PARALLEL_MAP.md](PARALLEL_MAP.md)

---

## Issue summary

| Category | Count | Severity |
|----------|-------|----------|
| Long files (>400 lines) | 5 | 🔴 High |
| NOT IMPLEMENTED / STUB | 9 | 🔴 High |
| Provider abstraction leaks (P1–P6) | 6 | 🔴 High |
| Missing provider implementations | 5 | 🔴 High |
| Config migration | 1 | 🔴 High |
| Code duplicates | 6 groups | 🟡 Medium |
| Flake8 E402 | 15 (1 script) | 🟢 Low |

---

## Steps — 1 file = 1 step

### Block A — Code quality (from comprehensive_analysis)

| Step | File | Issues | Depends on |
|------|------|--------|------------|
| [STEP-01](step-01_chat_flow.md) | `chat_flow.py` | 609 lines, monolith `run_chat_flow` | STEP-P1 |
| [STEP-02](step-02_config.md) | `config.py` | 477 lines, dup parsers | STEP-C1 |
| [STEP-03](step-03_ollama_chat_command.md) | `commands/ollama_chat_command.py` | 476 lines, dup schemas | STEP-01 |
| [STEP-04](step-04_get_model_context_command.md) | `commands/get_model_context_command.py` | 415 lines, placeholder | STEP-P1 |
| [STEP-05](step-05_docker_config_validation.md) | `docker_config_validation.py` | 527 lines, monolith | STEP-02 |
| [STEP-06](step-06_commercial_chat_client.md) | `commercial_chat_client.py` | 2× NOT IMPLEMENTED | STEP-P2 |
| [STEP-07](step-07_provider_registry.md) | `provider_registry.py` | 3× NOT IMPLEMENTED | STEP-06, STEP-P2 |
| [STEP-08](step-08_provider_client_base.md) | `provider_client_base.py` | dup abstract stubs | STEP-06, STEP-07 |
| [STEP-09](step-09_ollama_provider_client.md) | `ollama_provider_client.py` | dup normalize methods | STEP-08 |
| [STEP-10](step-10_documentation_slot_builder.md) | `documentation_slot_builder.py` | 2× STUB | — |
| [STEP-11](step-11_model_workspace_client_config_cli.md) | `model_workspace_client/config_cli.py` | dup arg parsers | — |
| [STEP-12](step-12_scripts_verify_context_formation.md) | `scripts/verify_context_formation.py` | 15× E402 | — |

### Block P — Provider abstraction (fix leaks P1–P6)

| Step | File / concern | What | Depends on |
|------|---------------|------|------------|
| [STEP-P1](step-p1_representation_registry_enforcement.md) | `chat_flow.py`, `ollama_chat_command.py`, `get_model_context_command.py`, `tools.py` | Fix P1+P5: route all representation through `RepresentationRegistry`; rename `get_ollama_tools` → `get_tools_for_model(model_id)` | — |
| [STEP-P2](step-p2_provider_registry_and_base.md) | `provider_registry.py`, `provider_client_base.py` | Fix P2+P3: implement `get_client()` for all 6 providers; remove `OllamaServer*Command` direct HTTP; enforce `BaseProviderClient` contract | STEP-08 |
| [STEP-P3](step-p3_openai_representation.md) | `openai_representation.py` (new) | `OpenAIRepresentation(ContextRepresentation)` + register for openai/xai/deepseek models | STEP-P1 |
| [STEP-P4](step-p4_anthropic_representation.md) | `anthropic_representation.py` (new) | `AnthropicRepresentation(ContextRepresentation)` | STEP-P1 |
| [STEP-P5](step-p5_gemini_representation.md) | `gemini_representation.py` (new) | `GeminiRepresentation(ContextRepresentation)` — Gemini function calling format | STEP-P1 |

### Block I — Provider implementations

| Step | File | Provider | Depends on |
|------|------|----------|------------|
| [STEP-I1](step-i1_openai_provider_client.md) | `openai_provider_client.py` (new) | openai — `/v1/chat/completions`, `/v1/embeddings` | STEP-08 |
| [STEP-I2](step-i2_anthropic_provider_client.md) | `anthropic_provider_client.py` (new) | anthropic — Messages API, no embed | STEP-08 |
| [STEP-I3](step-i3_google_provider_client.md) | `google_provider_client.py` (new) | Gemini API — `generateContent`, `embedContent` | STEP-08 |
| [STEP-I4](step-i4_xai_provider_client.md) | `xai_provider_client.py` (new) | xAI — OpenAI-compat, no embed | STEP-I1 |
| [STEP-I5](step-i5_deepseek_provider_client.md) | `deepseek_provider_client.py` (new) | DeepSeek — OpenAI-compat, no embed | STEP-I1 |

### Block C — Config migration

| Step | File | What | Depends on |
|------|------|------|------------|
| [STEP-C1](step-c1_config_migration.md) | `config.py`, `WorkstationConfig` | Remove `ollama_url`/`ollama_model`; parse `provider_clients` structure per standard; add per-provider validation V-PROV-1..6 | STEP-08 |

### Block S — Search

| Step | File | What | Depends on |
|------|------|------|------------|
| [STEP-S1](step-s1_search_command.md) | `commands/search_command.py` (new) | `search` MCP command: semantic/bm25/hybrid modes, `filter_expr` via `ChunkQuery` DSL, resolve via FAISS→lookup→Redis | STEP-I1 (embed), STEP-P1 |
| [STEP-S2](step-s2_faiss_lookup_table.md) | `vectorization_client.py`, Redis schema | FAISS↔chunk_uuid lookup table in Redis; rebuild-from-Redis support | STEP-S1 |

---

## Legend

- 🔴 **High** — blocks functionality or violates contract
- 🟡 **Medium** — maintainability
- 🟢 **Low** — style
