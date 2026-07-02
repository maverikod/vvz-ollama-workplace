# Design: Model workspace (data flow and config)

**Author:** Vasiliy Zdanovskiy  
**Email:** vasilyvz@gmail.com  

This document describes the **model workspace** only: how it uses **provider clients** (mwps_provider_client, redis_provider_client) and the **proxy client**, and how it is configured. For the workspace, **Model Workplace Server server is just a separate provider**. It does not describe Redis or Model Workplace Server internals. Aligned with [SPEC §4, §5, §8](../../docs/plans/refactoring_adapter_structure/SPEC.md).

---

## Chosen option

**Option A (adapter Command):** The workspace is exposed as an adapter Command (e.g. `mwps_chat`) that accepts `messages`, optional `model`, `stream`, `max_tool_rounds`; uses the **proxy client** for MCP Proxy tool execution and a **provider client** (e.g. mwps_provider_client) for chat; returns the final assistant message and full history.

**Option B:** Standalone service (e.g. FastAPI) with an endpoint such as `POST /mwps/chat`, same flow inside; may register with the proxy as a server.

---

## Data flow (workspace only)

1. Client sends a request to the adapter (or to the workspace endpoint) with method `mwps_chat` and params `{ "messages": [...], "model": "?", ... }`.
2. The adapter handles auth and request/response; the command receives validated params.
3. **Workspace** loads config, builds **context** (see [context_formation.md](context_formation.md)), then runs the chat flow.
4. **Chat flow:**
   - Build chat request for the **provider client** (e.g. mwps_provider_client: model, messages, tools from workspace tool definitions).
   - **Provider client** returns a message that may contain `tool_calls`.
   - For each tool call, the workspace calls the **MCP Proxy** via **proxy client** (list_servers, call_server, or help), then appends a tool message to the conversation.
   - Repeat until the model returns no `tool_calls` or `max_tool_rounds` is reached.
5. Return the final message and history to the adapter, which serializes it in the response.

---

## Config (workspace)

| Field | Required | Description |
|-------|----------|-------------|
| mcp_proxy_url | Yes | Base URL of the MCP Proxy (e.g. `http://localhost:3004`). |
| provider_clients (Model Workplace Server, etc.) | Yes | Config for each provider (Model Workplace Server = one provider; server id, model, timeouts); see root [provider_client_config_standard.md](../../docs/standards/provider_client_config_standard.md). |
| mwps_model (or default model) | Yes | Default model name for chat (e.g. `llama3.1`). |
| mwps_timeout | No | Timeout in seconds for chat requests (default 60). |
| max_tool_rounds | No | Max tool-call rounds per chat (default 10). |
| Context parameters | No | max_context_tokens, last_n_messages, min_semantic_tokens, etc.; see [context_formation.md](context_formation.md). |
| proxy_token, proxy_token_header | No | Proxy auth if required. |

Source: config file (YAML/JSON) or environment variables. Single place; no hardcoded URLs.

---

## Proxy API (used by workspace)

The workspace assumes the MCP Proxy exposes (e.g. at `{proxy_url}/api/jsonrpc` or REST):

- **list_servers** — params: page, page_size, filter_enabled (optional). Returns e.g. `{ "servers": [...] }`.
- **call_server** — params: server_id, command, optional copy_number, optional params. Returns the command result.
- **help** — params: server_id, optional copy_number, optional command. Returns help text or structure.

The **proxy client** used by the workspace must match the proxy’s actual API (JSON-RPC or REST); config (URL, TLS, timeouts) is shared.

---

## Optional: register workspace with MCP Proxy

So that external clients can call “chat with model + MCP tools” via the proxy: configure the adapter’s proxy registration so that the server that runs the workspace command registers with the MCP Proxy at startup. Then clients call the proxy, which routes to this server and thus to the workspace command. Registration and mTLS are **common** to all adapters; see root [registration_troubleshooting.md](../../docs/registration_troubleshooting.md) and [container_usage.md](../../docs/container_usage.md).
