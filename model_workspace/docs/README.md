# model_workspace — documentation

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

Documentation for the **model_workspace** subproject only. Stack-wide topics (Redis, Model Workplace Server, containers, registration, mTLS, provider client standards) are in **root** `docs/`.

**Per SPEC §4, §5:** The **model-workspace-server** uses **provider client** packages (mwps_provider_client, redis_provider_client). **For the model workspace, Model Workplace Server server is just a separate provider.** No Redis or Model Workplace Server inside. Canonical plan: [docs/plans/refactoring_adapter_structure/SPEC.md](../../docs/plans/refactoring_adapter_structure/SPEC.md).

---

## Technical specification (ТЗ)

**[ТЗ.md](ТЗ.md)** — technical specification for this subproject: model workspace application using **mwps_provider_client** and **redis_provider_client** (Model Workplace Server = one provider); configuration, container **model-workspace-server**, overview.

---

## Workspace-only docs (this subproject)

| Doc | Description |
|-----|-------------|
| **[techspec.md](techspec.md)** | Workspace role, tools (list_servers, call_server, help), chat flow, config. No Redis/MWPS internals. |
| **[design.md](design.md)** | Data flow: workspace → provider clients (Model Workplace Server, Redis), workspace → proxy client. Config. |
| **[context_formation.md](context_formation.md)** | Context building (ContextBuilder), limits, segment order, relevance slot, token usage. |
| **[deployment.md](deployment.md)** | How to run the workspace; **links to root** for stack, registration, mTLS. |

---

## Common / stack-wide (root docs)

These live in the **repository root** `docs/`, not here. The workspace **uses** them; it does not duplicate them.

| Topic | Location |
|-------|----------|
| Stack (containers, MWPS, Redis, build/run, mTLS) | Root [docs/container_usage.md](../../docs/container_usage.md) |
| Registration, “Proxy not available” | Root [docs/registration_troubleshooting.md](../../docs/registration_troubleshooting.md) |
| Provider client API (normative) | Root [docs/standards/provider_client_standard.md](../../docs/standards/provider_client_standard.md) |
| Provider client config (normative) | Root [docs/standards/provider_client_config_standard.md](../../docs/standards/provider_client_config_standard.md) |

---

## Other

- **reports/** — AI-generated reports (отчёты ИИ). Do not use for hand-written docs.
- **plans/** — implementation plans, roadmaps.
