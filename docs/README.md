# Root documentation — integration (сопряжение) of subprojects

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

In the **root** `docs/` only documents that concern **coupling/integration** of subprojects are kept. Subproject-specific content lives in each subproject’s `docs/`.

**Start here:** [SUBPROJECTS_OVERVIEW.md](SUBPROJECTS_OVERVIEW.md) — overview of the six subproject categories, principle “all clients on adapter client base, hide provider specifics”, and where to find what.

---

## Documents (сопряжение проектов)

| Document | Description |
|----------|-------------|
| **[SUBPROJECTS_OVERVIEW.md](SUBPROJECTS_OVERVIEW.md)** | **Main overview:** six subproject categories, clients on adapter client base, hide provider specifics, dependencies. |
| **[project_structure.md](project_structure.md)** | Layout: root and subprojects; containers; references to overview. |
| **[container_usage.md](container_usage.md)** | Running the full stack (redis-adapter, ollama-adapter, model-workspace-server); build, run, mTLS, networks. |
| **[registration_troubleshooting.md](registration_troubleshooting.md)** | Registration with MCP proxy; "Proxy not available"; mTLS and checklist (common to all adapters). |
| **[standards/provider_client_standard.md](standards/provider_client_standard.md)** | Normative API of provider clients (chat, embed, healthcheck, errors) — contract between model_workspace and **provider client** packages (e.g. ollama_provider_client). |
| **[standards/provider_client_config_standard.md](standards/provider_client_config_standard.md)** | Normative structure and validation of `provider_clients` config — shared by model_workspace and provider clients. |
| **[plans/refactoring_adapter_structure/SPEC.md](plans/refactoring_adapter_structure/SPEC.md)** | Target architecture (Russian): five subprojects, WebSocket, tunnel mode, **provider clients** (ollama_provider_client, redis_provider_client); for model_workspace Ollama is just one provider. |

---

## Other files in root docs

- **RULES.md** — project-wide code and layout rules (apply to all subprojects).
- **standards.md** — tool format, config conventions (workstation integration with proxy).
- **ollama_setup.md** — OLLAMA install/verify on host; reference to container_usage for stack.

---

## Per-subproject documentation

- **model_workspace/docs/** — ТЗ, techspec, design, context_formation, deployment (uses provider clients; Ollama = one provider).
- **ollama_adapter/docs/** — ТЗ, README (server).
- **redis_adapter/docs/** — ТЗ, README (server); [SPEC_HIGH_LEVEL_DATABASE_API.md](../redis_adapter/docs/SPEC_HIGH_LEVEL_DATABASE_API.md) — high-level database API (sessions, messages) and client on adapter+WebSocket.
- **ollama_provider_client/docs/** — ТЗ, README (provider client for Ollama).
- **redis_provider_client/docs/** — ТЗ, README (provider client for Redis storage).

Per-subproject **docker/** (build image, run container) for server subprojects — see each subproject’s `docker/` and root [container_usage.md](container_usage.md) for the full stack. Provider client subprojects are libraries; no container.
