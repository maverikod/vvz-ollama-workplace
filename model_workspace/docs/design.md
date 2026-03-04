# Design: Model workspace (data flow and config)

**Author:** Vasiliy Zdanovskiy  
**Email:** vasilyvz@gmail.com  

This document describes the **model workspace** only: how it uses the **client to ollama-adapter** and the **proxy client**, and how it is configured. It does not describe Redis or Ollama internals. Aligned with [SPEC §4, §8](../../docs/plans/refactoring_adapter_structure/SPEC.md).

---

## Chosen option

**Option A (adapter Command):** The workspace is exposed as an adapter Command (e.g. `ollama_chat`) that accepts `messages`, optional `model`, `stream`, `max_tool_rounds`; uses the **proxy client** for MCP Proxy tool execution and the **client to ollama-adapter** for chat; returns the final assistant message and full history.

**Option B:** Standalone service (e.g. FastAPI) with an endpoint such as `POST /ollama/chat`, same flow inside; may register with the proxy as a server.

---

## Data flow (workspace only)

1. Client sends a request to the adapter (or to the workspace endpoint) with method `ollama_chat` and params `{ "messages": [...], "model": "?", ... }`.
2. The adapter handles auth and request/response; the command receives validated params.
3. **Workspace** loads config, builds **context** (see [context_formation.md](context_formation.md)), then runs the chat flow.
4. **Chat flow:**
   - Build chat request for the **client to ollama-adapter** (model, messages, tools from workspace tool definitions).
   - **Client to ollama-adapter** returns a message that may contain `tool_calls`.
   - For each tool call, the workspace calls the **MCP Proxy** via **proxy client** (list_servers, call_server, or help), then appends a tool message to the conversation.
   - Repeat until the model returns no `tool_calls` or `max_tool_rounds` is reached.
5. Return the final message and history to the adapter, which serializes it in the response.

---

## Config (workspace)

| Field | Required | Description |
|-------|----------|-------------|
| mcp_proxy_url | Yes | Base URL of the MCP Proxy (e.g. `http://localhost:3004`). |
| Client to ollama-adapter config | Yes | Connection to ollama-adapter via proxy (server id, model, timeouts); see root [provider_client_config_standard.md](../../docs/standards/provider_client_config_standard.md). |
| ollama_model (or default model) | Yes | Default model name for chat (e.g. `llama3.1`). |
| ollama_timeout | No | Timeout in seconds for chat requests (default 60). |
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
