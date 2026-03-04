# Root documentation — integration (сопряжение) of subprojects

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

In the **root** `docs/` only documents that concern **coupling/integration of the three subprojects** (model_workspace, ollama_adapter, redis_adapter) are kept. Subproject-specific content lives in each subproject’s `docs/`.

---

## Documents (сопряжение проектов)

| Document | Description |
|----------|-------------|
| **[project_structure.md](project_structure.md)** | Layout: root and three subprojects; containers; where docs and code live. |
| **[container_usage.md](container_usage.md)** | Running the full stack (redis-adapter, ollama-adapter, model-workspace-server); build, run, mTLS, networks. |
| **[registration_troubleshooting.md](registration_troubleshooting.md)** | Registration with MCP proxy; "Proxy not available"; mTLS and checklist (common to all adapters). |
| **[standards/provider_client_standard.md](standards/provider_client_standard.md)** | Normative API of provider clients (chat, embed, healthcheck, errors) — contract between model_workspace and ollama_adapter (and other model providers). |
| **[standards/provider_client_config_standard.md](standards/provider_client_config_standard.md)** | Normative structure and validation of `provider_clients` config — shared by model_workspace and adapters. |
| **[plans/refactoring_adapter_structure/SPEC.md](plans/refactoring_adapter_structure/SPEC.md)** | Target architecture (Russian): three containers, WebSocket, tunnel mode, client/server roles. |

---

## Other files in root docs

- **RULES.md** — project-wide code and layout rules (apply to all subprojects).
- **standards.md** — tool format, config conventions (workstation integration with proxy).
- **ollama_setup.md** — OLLAMA install/verify on host; reference to container_usage for stack.

---

## Per-subproject documentation

- **model_workspace/docs/** — ТЗ, techspec, design, context_formation, deployment.
- **ollama_adapter/docs/** — ТЗ, README.
- **redis_adapter/docs/** — ТЗ, README.

Per-subproject **docker/** (build image, run container) — see each subproject’s `docker/` and root [container_usage.md](container_usage.md) for the full stack.
