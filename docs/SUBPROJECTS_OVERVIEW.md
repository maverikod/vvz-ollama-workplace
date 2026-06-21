# Subprojects overview

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

This document is the **main project overview**: it describes the subproject layout, the principle that **all clients are based on the adapter client** and hide provider-specific format and API, and the six categories of subprojects. For integration (containers, registration, standards) see [README.md](README.md) and [project_structure.md](project_structure.md). Canonical plan: [plans/refactoring_adapter_structure/SPEC.md](plans/refactoring_adapter_structure/SPEC.md).

---

## 1. Purpose of splitting into subprojects

- **Servers** (Ollama + adapter, Redis + adapter, model workspace) run in separate containers; each has its own codebase and dependencies.
- **Clients** are separated so that **provider-specific details and format** stay inside the client. The model workspace (and any other consumer) uses only a uniform or provider-agnostic API; transport, serialization, and protocol to the adapter are hidden in the client.
- **All clients are based on the adapter client** (from mcp-proxy-adapter): WebSocket to the adapter server, same command/response protocol. Each client package wraps this base with the provider’s API (Ollama methods, Redis commands, or provider_client_standard for model providers).

---

## 2. Six categories of subprojects

| # | Category | Subdirectory | Description |
|---|----------|--------------|-------------|
| **1** | Ollama server + adapter | **ollama_adapter/** | Server: Ollama process + mcp-proxy-adapter API. Registers with MCP Proxy; exposes Ollama API over WebSocket. No client code in this project; only the server. Container: **ollama-adapter**. |
| **2** | Redis server + adapter | **redis_adapter/** | Server: Redis process + mcp-proxy-adapter API. Registers with MCP Proxy; exposes Redis commands over WebSocket. No client code in this project; only the server. Container: **redis-adapter**. |
| **3** | Model workspace (server) | **model_workspace/** | Application “model workspace”: chat orchestration, session, context, MCP Proxy tools. Uses **provider clients** (Ollama, Redis, optionally others). Contains no Redis or Ollama; for it, **Ollama is just one provider**. Container: **model-workspace-server**. |
| **4** | Ollama client (on adapter client base) | **ollama_provider_client/** | Client for Ollama: chat, embed, healthcheck, etc. **Based on the adapter client** (WebSocket to ollama-adapter). Hides Ollama/adapter format and transport. Implements [provider_client_standard](standards/provider_client_standard.md). Used by model_workspace. Library only; no container. |
| **5** | Redis client (on adapter client base) | **redis_provider_client/** | Client for Redis (storage): execute(command, *args) + wrappers (get, set, hgetall, …). **Based on the adapter client** (WebSocket to redis-adapter). Hides Redis/adapter format and transport. Used by model_workspace. Library only; no container. |
| **6** | Other provider clients | **&lt;name&gt;_provider_client/** | Future subdirectories for other providers (e.g. openai_provider_client, anthropic_provider_client). Each is **based on the adapter client**, hides that provider’s format and API; implements provider_client_standard where applicable. Used by model_workspace or other consumers. |

---

## 3. Adapter client as base for all clients

- **Adapter client** = the client from **mcp-proxy-adapter** (or a thin wrapper): connects to an adapter server over **WebSocket** (via proxy), sends commands and receives responses. Same transport and protocol for every adapter server.
- **Ollama client** (ollama_provider_client): uses the adapter client to talk to **ollama-adapter**; exposes Ollama-style API (chat, embed, tags, …). Provider-specific request/response format and errors are **inside** this package.
- **Redis client** (redis_provider_client): uses the adapter client to talk to **redis-adapter**; exposes Redis-style API (get, set, execute, …). Redis command/response format is **inside** this package.
- **Other provider clients**: same idea — adapter client + provider-specific API and format hidden inside the package.

So: **one base (adapter client), many client packages** that hide provider specifics.

---

## 4. Dependencies between subprojects

```
model_workspace
    ├── ollama_provider_client   (Ollama = one provider)
    ├── redis_provider_client    (storage)
    ├── (optional) other *_provider_client
    └── mcp-proxy-adapter        (proxy client for list_servers, call_server, help)

ollama_provider_client
    └── mcp-proxy-adapter / adapter client (WebSocket to ollama-adapter)

redis_provider_client
    └── mcp-proxy-adapter / adapter client (WebSocket to redis-adapter)

ollama_adapter (server)  — no dependency on model_workspace or clients
redis_adapter (server)   — no dependency on model_workspace or clients
```

Containers: **ollama-adapter**, **redis-adapter**, **model-workspace-server** (see [container_usage.md](container_usage.md)).

---

## 5. Where to find what

| Topic | Location |
|-------|----------|
| This overview | **docs/SUBPROJECTS_OVERVIEW.md** (this file) |
| Plan (Russian, full) | [docs/plans/refactoring_adapter_structure/SPEC.md](plans/refactoring_adapter_structure/SPEC.md) |
| Root layout, containers | [docs/project_structure.md](project_structure.md) |
| Integration (stack, registration, standards) | [docs/README.md](README.md) |
| Model workspace ТЗ | model_workspace/docs/ТЗ.md |
| Ollama adapter ТЗ | ollama_adapter/docs/ТЗ.md |
| Redis adapter ТЗ | redis_adapter/docs/ТЗ.md |
| Redis adapter — high-level database API (ТЗ) | [redis_adapter/docs/SPEC_HIGH_LEVEL_DATABASE_API.md](redis_adapter/docs/SPEC_HIGH_LEVEL_DATABASE_API.md) |
| Ollama provider client ТЗ | ollama_provider_client/docs/ТЗ.md |
| Redis provider client ТЗ | redis_provider_client/docs/ТЗ.md |
| Provider client API (normative) | [docs/standards/provider_client_standard.md](standards/provider_client_standard.md) |
| Provider client config | [docs/standards/provider_client_config_standard.md](standards/provider_client_config_standard.md) |

---

## 6. Summary

- **Six categories:** (1) Ollama server+adapter, (2) Redis server+adapter, (3) model workspace server, (4) Ollama client on adapter client base, (5) Redis client on adapter client base, (6) other provider clients in their own subdirs.
- **Clients** are in separate projects; each client **hides provider-specific format and API** and is **based on the adapter client** (WebSocket, same protocol).
- **Model workspace** uses only these client packages; for it, Ollama is just one provider among others.
