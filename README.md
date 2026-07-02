# Agent Workstation — monorepo

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

Monorepo for the Agent Workstation: servers (Model Workplace Server+adapter, Redis+adapter, model workspace) and **provider clients** (Model Workplace Server, Redis, others). All clients are **based on the adapter client** (mcp-proxy-adapter) and hide provider-specific format and API.

---

## Subprojects (six categories)

| # | Category | Subdirectory |
|---|----------|--------------|
| 1 | Model Workplace Server server + adapter | **mwps_adapter/** |
| 2 | Redis server + adapter | **redis_adapter/** |
| 3 | Model workspace (server) | **model_workspace/** |
| 4 | Model Workplace Server client (on adapter client base) | **mwps_provider_client/** |
| 5 | Redis client (on adapter client base) | **redis_provider_client/** |
| 6 | Other provider clients | **&lt;name&gt;_provider_client/** (e.g. openai_provider_client) |

**Full overview and description:** [docs/SUBPROJECTS_OVERVIEW.md](docs/SUBPROJECTS_OVERVIEW.md).

**Plan (Russian):** [docs/plans/refactoring_adapter_structure/SPEC.md](docs/plans/refactoring_adapter_structure/SPEC.md).

**Integration (containers, registration, standards):** [docs/README.md](docs/README.md).

---

## Root contents

- **docs/** — common documentation (overview, integration, plans). No app code.
- **mtls_certificates/** — shared mTLS certs for adapters.

Each subproject has its own `docs/`, `src/`, `tests/`, `config/`, `pyproject.toml`, and is suitable for PyPI.
