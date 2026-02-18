# Design: OLLAMA workstation (Option A — adapter Command)

**Author:** Vasiliy Zdanovskiy  
**Email:** vasilyvz@gmail.com  

## Chosen option

**Option A:** Implement an adapter Command `ollama_chat` that accepts `messages`, optional `model`, `stream`, `max_tool_rounds`; uses the adapter’s client for MCP Proxy tool execution and a separate HTTP client for OLLAMA `/api/chat`; returns the final assistant message and full history.

## Data flow

1. Client sends a JSON-RPC request to the adapter with method `ollama_chat` and params `{ "messages": [...], "model": "?", ... }`.
2. The adapter (middleware) handles auth and request/response; the command receives validated params.
3. `OllamaChatCommand.execute()` loads workstation config, then calls `run_chat_flow()`.
4. **Chat flow:**
   - Build request to OLLAMA `POST /api/chat` with `model`, `messages`, `tools` (from `tools.get_ollama_tools()`).
   - OLLAMA may return a message with `tool_calls`.
   - For each tool call, the workstation calls the MCP Proxy (`list_servers`, `call_server`, or `help`) via `ProxyClient`, then appends a tool message `{ "role": "tool", "tool_name": "<name>", "content": "<result>" }` to the conversation.
   - Repeat until the model returns no `tool_calls` or `max_tool_rounds` is reached.
5. Return `SuccessResult(data={ "message": "<final>", "history": [...] })` to the adapter, which serializes it in the JSON-RPC response.

## Config

| Field | Required | Description |
|-------|----------|-------------|
| mcp_proxy_url | Yes | Base URL of the MCP Proxy (e.g. `http://localhost:3004`). |
| ollama_base_url | Yes | Base URL of OLLAMA (e.g. `http://localhost:11434`). |
| ollama_model | Yes | Default model name (e.g. `llama3.1`). |
| ollama_timeout | No | Timeout in seconds for OLLAMA requests (default 60). |
| max_tool_rounds | No | Max tool-call rounds per chat (default 10). |
| proxy_token, proxy_token_header | No | Proxy auth if required. |
| ollama_api_key | No | OLLAMA API key if required. |

Source: config file (YAML/JSON) or environment variables `OLLAMA_WORKSTATION_*`. Single place; no hardcoded URLs.

## Proxy API (list_servers, call_server, help)

The workstation assumes the MCP Proxy exposes JSON-RPC at `{proxy_url}/api/jsonrpc` with methods:

- **list_servers** — params: `page`, `page_size`, `filter_enabled` (all optional). Returns e.g. `{ "servers": [...] }`.
- **call_server** — params: `server_id`, `command`, optional `copy_number` (default 1), optional `params`. Returns the command result.
- **help** — params: `server_id`, optional `copy_number`, optional `command`. Returns help text or structure.

If the proxy uses a different API (e.g. OpenAPI REST), the thin client in `proxy_client.py` must be adapted to the proxy’s endpoints and payloads; config (URL, TLS, timeouts) is reused.

## Optional: register workstation with MCP Proxy (ТЗ 1.2)

So that external clients can call “chat with OLLAMA + MCP tools” via the proxy: configure the adapter’s proxy registration (e.g. `registration` or `proxy_client` section in the app config) so that the server that runs the `ollama_chat` command registers with the MCP Proxy at startup. Then clients call the proxy, which routes to this server and thus to `ollama_chat`. See the adapter docs for registration section format.
