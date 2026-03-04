# Config settings: full list and dependency graph

**Author:** Vasiliy Zdanovskiy  
**Email:** vasilyvz@gmail.com  
**Source:** Code analysis (config.py, docker_config_validation.py, docker/generate_config.py, mcp_proxy_adapter).

## 1. Where validation and generation live

- **Base (adapter):** `mcp_proxy_adapter` — `SimpleConfig.load()` + `SimpleConfig.validate()` (server, registration, SSL, etc.). Used first in `run_adapter.py`.
- **Project:** `ollama_workstation.docker_config_validation.validate_project_config(app_config)` — runs after adapter validation. Only checks project-specific and `ollama_workstation` keys.
- **Generation:** `docker/generate_config.py` and `container/generate_config.py` use adapter `SimpleConfigGenerator.generate(...)` for base config, then patch `server`, `transport`, and `ollama_workstation`.

## 2. Full list of settings (ollama_workstation + server/transport)

| Key | Required | Type | When optional becomes required | Generator | Validator |
|-----|----------|------|---------------------------------|-----------|-----------|
| **ollama_workstation** | — | section | — | ✓ | — |
| mcp_proxy_url | yes | string | always | ✓ | (adapter) |
| ollama_base_url | yes | string | always | ✓ | (adapter) |
| ollama_model | yes | string | always | ✓ | (adapter) |
| ollama_timeout | no | number | — | ✓ | — |
| max_tool_rounds | no | int ≥ 1 | — | ✓ | — |
| proxy_token | no | string | — | no | — |
| proxy_token_header | no | string | — | no | — |
| ollama_api_key | no | string | — | no | — |
| allowed_commands | no | list[str] | — | ✓ | ✓ |
| forbidden_commands | no | list[str] | — | ✓ | ✓ |
| commands_policy | no | "allow_by_default" \| "deny_by_default" | — | ✓ | ✓ |
| command_discovery_interval_sec | no | int ≥ 0 | — | ✓ | ✓ |
| session_store_type | no | string | — | ✓ | ✓ |
| redis_host | no | string | — | ✓ | ✓ |
| redis_port | no | int 1–65535 | — | ✓ | ✓ |
| redis_password | no | string | — | ✓ (if env set) | — |
| redis_key_prefix | no | string | — | ✓ | ✓ |
| ollama_models | no | list[non-empty str] | if present: must be list of non-empty strings | ✓ | ✓ |
| max_context_tokens | no | int ≥ 0 | — | ✓ | ✓ |
| last_n_messages | no | int ≥ 0 | — | ✓ | ✓ |
| min_semantic_tokens | no | int ≥ 0 | — | ✓ | ✓ |
| min_documentation_tokens | no | int ≥ 0 | — | ✓ | ✓ |
| relevance_slot_mode | no | "fixed_order" \| "unified_by_relevance" | — | ✓ | ✓ |
| max_model_call_depth | no | int ≥ 0 | — | ✓ | ✓ |
| model_calling_tool_allow_list | no | list[str] | if present: must be list of strings | ✓ | ✓ |
| **server** | — | section | — | adapter | adapter |
| server.protocol | — | "http" \| "mtls" | — | ✓ | — |
| server.ssl.cert, server.ssl.key | no | string (path) | **required if server.protocol == "mtls"** | ✓ | ✓ |
| **transport** | — | section | — | ✓ | ✓ |
| transport.verify_client | no | bool | **required true if protocol == "mtls"** | ✓ | ✓ |

## 3. Optional → required conditions (validator behaviour)

- **If `server.protocol == "mtls"`:**
  - `server.ssl.cert` and `server.ssl.key` must be set.
  - `transport.verify_client` must be true.
- **If `ollama_workstation.ollama_models` is present:**
  - Must be a list; each element must be a non-empty string.
- All other listed keys are optional; when present, type/range are validated as in the table. No other “optional becomes required” rules are implemented.

## 4. Dependency graph (conceptual)

```
                    [Adapter SimpleConfigGenerator]
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │ server, registration, SSL     │
                    └───────────────────────────────┘
                                    │
                    [Project overlay: docker/container generate_config.py]
                                    │
                                    ▼
    ┌───────────────────────────────────────────────────────────────────┐
    │ ollama_workstation                                                 │
    │   mcp_proxy_url, ollama_base_url, ollama_model  ← required         │
    │   ollama_models, ollama_timeout, max_tool_rounds                   │
    │   commands_policy, allowed_commands, forbidden_commands            │
    │   command_discovery_interval_sec, session_store_type                │
    │   redis_host, redis_port, redis_password?, redis_key_prefix        │
    │   max_context_tokens, last_n_messages, min_semantic_*, ...          │
    │   relevance_slot_mode, max_model_call_depth, model_calling_*        │
    └───────────────────────────────────────────────────────────────────┘
                                    │
                    [load_config() reads file + env → WorkstationConfig]
                                    │
                    [validate: adapter validate() then validate_project_config()]
```

## 5. Generator vs validator alignment

- **Generator (docker + container):** Emit all `ollama_workstation` keys used by `load_config()`; optional `redis_password` only if env `OLLAMA_WORKSTATION_REDIS_PASSWORD` is set. Both generators include `ollama_models`.
- **Validator:** Checks types/ranges for all optional keys when present; enforces “if mtls then ssl + verify_client” and “if ollama_models present then list of non-empty strings”. `model_calling_tool_allow_list`, `redis_host`, `redis_key_prefix` validated when present.
