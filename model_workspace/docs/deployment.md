# Model workspace: deployment and run

**Author:** Vasiliy Zdanovskiy  
**Email:** vasilyvz@gmail.com  

This document describes **only** how to run the **model workspace** (this subproject). Stack-wide topics (Redis, OLLAMA, all adapters, registration, mTLS) are in **root docs**.

---

## What this subproject is

The **model_workspace** is the application (container **model-workspace-server** per SPEC §4) that uses **client to redis-adapter** and **client to ollama-adapter** (WebSocket via proxy). It does **not** run Redis or Ollama inside. See [ТЗ.md](ТЗ.md), [techspec.md](techspec.md), and root [SPEC](../../docs/plans/refactoring_adapter_structure/SPEC.md).

---

## Running the workspace

- **As part of the full stack:** Use the root project’s Docker and scripts. See root **[docs/container_usage.md](../../docs/container_usage.md)** for build, run, networks, mounts, and mTLS.
- **Registration with MCP proxy:** Common for all adapters. See root **[docs/registration_troubleshooting.md](../../docs/registration_troubleshooting.md)** when you see “Proxy not available”.
- **Config:** Workspace config (mcp_proxy_url, client to ollama-adapter / redis-adapter, model, context limits) is part of the adapter or app config; see [design.md](design.md) and root [provider_client_config_standard](../../docs/standards/provider_client_config_standard.md).

---

## Summary

| Topic | Where |
|-------|--------|
| Full stack (containers, OLLAMA, Redis, adapter) | Root [docs/container_usage.md](../../docs/container_usage.md) |
| Registration, mTLS, “Proxy not available” | Root [docs/registration_troubleshooting.md](../../docs/registration_troubleshooting.md) |
| Provider client API contract | Root [docs/standards/provider_client_standard.md](../../docs/standards/provider_client_standard.md) |
| Provider client config structure | Root [docs/standards/provider_client_config_standard.md](../../docs/standards/provider_client_config_standard.md) |
| Workspace role, tools, chat flow | [techspec.md](techspec.md), [design.md](design.md) |
| Context building | [context_formation.md](context_formation.md) |
