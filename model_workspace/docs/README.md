# model_workspace — documentation

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

Documentation and guides for the model_workspace subproject.

---

## Technical specification (ТЗ)

**[ТЗ.md](ТЗ.md)** — technical specification for the subproject: model workspace application using redis_adapter and ollama_adapter clients (no Redis or Ollama inside), configuration, container, overview of functionality.

General context (cluster, three subprojects): repository root `docs/plans/refactoring_adapter_structure/SPEC.md`.

---

## Workstation docs (moved from root docs)

- **[techspec.md](techspec.md)** — technical specification: OLLAMA workstation, tools (list_servers, call_server, help), chat flow, config, integration with mcp-proxy-adapter.
- **[design.md](design.md)** — design Option A: adapter Command `ollama_chat`, data flow, config, proxy API.
- **[context_formation.md](context_formation.md)** — context building (ContextBuilder), limits, segment order, relevance slot, token usage logging.
- **[container_usage.md](container_usage.md)** — running OLLAMA + Redis + adapter container, registration, mTLS, test container, commercial models.
- **[registration_troubleshooting.md](registration_troubleshooting.md)** — "Proxy not available", CA, mTLS, checklist.
- **standards/** — provider client and config standards:
  - [provider_client_standard.md](standards/provider_client_standard.md) — normative API for provider clients (chat, embed, healthcheck, errors).
  - [provider_client_config_standard.md](standards/provider_client_config_standard.md) — provider_clients config structure and validation.

---

## Other

- **reports/** — AI-generated reports (отчёты ИИ). Do not use for hand-written docs.
- **plans/** — implementation plans, roadmaps.
