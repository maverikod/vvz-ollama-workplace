# Technical specification: OLLAMA interface for MCP-Proxy-Adapter (OLLAMA workstation)

**Author:** Vasiliy Zdanovskiy  
**Email:** vasilyvz@gmail.com  

---

## 1. Purpose and scope

### 1.1 Purpose

Add to **mcp-proxy-adapter** (or deliver as an extension/companion) an **OLLAMA interface** so that:

- **OLLAMA** (the LLM running in OLLAMA) can **use the MCP Proxy** as its tool backend.
- The model receives **tools** that are implemented by calling the MCP Proxy (e.g. `list_servers`, `call_server`, `help`).
- When the model returns **tool calls**, the adapter executes them against the MCP Proxy and feeds the results back to OLLAMA, forming a **working station** where OLLAMA can discover and invoke any server registered in the proxy.

So: **on top of the adapter, build a workstation for OLLAMA that can talk to the MCP Proxy.**

**Role of the model:** The OLLAMA model is used **as the agent’s tool** (e.g. by Cursor or another AI client). For that to be useful, the model must receive **relevant context** — not only the last N messages, but also past turns that are **semantically relevant** to the current request. Without embedding-based relevance (vectorization + relevance slot), the model cannot use long dialogue history effectively and is of little value as a tool. Therefore the **embedding service** and **relevance slot by vector similarity** are essential for the workstation, not optional.

### 1.2 Scope

- **In scope:** Design and implementation of a component that (1) connects to OLLAMA (chat API with tools), (2) injects MCP-Proxy tools into requests, (3) handles OLLAMA tool_calls by calling the MCP Proxy, (4) optionally registers itself with the MCP Proxy so that external clients can “chat with OLLAMA + MCP tools” via the proxy. Configuration (proxy URL, OLLAMA URL, model name). Documentation and a minimal example.
- **Out of scope:** Modifying OLLAMA source code; implementing the MCP protocol from scratch; supporting every OLLAMA API (focus on `/api/chat` with tools). Other backends (e.g. OpenAI) are not required by this ТЗ.

### 1.3 Goals

1. OLLAMA (the model) can **list** servers and **call** commands on any server registered in the MCP Proxy.
2. The solution is **based on mcp-proxy-adapter** (reuse its client to talk to the proxy, and optionally expose a Command that runs “chat with OLLAMA + proxy tools”).
3. Single place of configuration: MCP Proxy URL, OLLAMA base URL, model name, timeouts.

---

## 2. Functional requirements

### 2.1 Tools exposed to OLLAMA

The following tools must be provided to OLLAMA in every relevant chat request. They are implemented by calling the MCP Proxy.

| Tool name       | Description (for model) | Parameters (JSON Schema) | Proxy call |
|-----------------|-------------------------|---------------------------|------------|
| **list_servers** | List servers registered in the MCP Proxy (optionally filtered). | `page` (integer, optional), `page_size` (integer, optional), `filter_enabled` (boolean, optional) | MCP Proxy `list_servers` (or equivalent). |
| **call_server**  | Execute a command on a registered server. | `server_id` (string), `copy_number` (integer, optional, default 1), `command` (string), `params` (object, optional) | MCP Proxy `call_server`. |
| **help**         | Get help/usage for a server or a specific command. | `server_id` (string), `copy_number` (integer, optional), `command` (string, optional) | MCP Proxy `help`. |

Additional proxy tools (e.g. `health_check`, `network_check`) may be added later; the above three are mandatory for a minimal “workstation”.

### 2.2 Chat flow with tools

1. Client (or adapter command) sends a chat request to the **OLLAMA workstation** (not directly to OLLAMA).
2. The workstation builds a request to **OLLAMA** `/api/chat` with:
   - `model`, `messages`, `stream` (optional),
   - `tools` = array of tool definitions (list_servers, call_server, help) in OLLAMA format: `{ "type": "function", "function": { "name", "description", "parameters" } }`.
3. OLLAMA returns a message that may contain `tool_calls`.
4. For each tool call, the workstation **calls the MCP Proxy** (using the adapter’s existing client or HTTP client configured with proxy URL), obtains the result, and appends a message `{ "role": "tool", "tool_name": "<name>", "content": "<result>" }` to the conversation.
5. Repeat from step 2 (send updated messages to OLLAMA) until the model returns a message without tool_calls or a maximum iteration count is reached.
6. The final model reply (and optionally the full message history) is returned to the caller.

### 2.3 Integration with mcp-proxy-adapter

- **Option A (recommended):** Implement an **adapter Command** (e.g. `ollama_chat` or `ollama_chat_with_proxy_tools`) that:
  - Accepts params: `messages` (array), `model` (optional), `stream` (optional), `max_tool_rounds` (optional).
  - Uses the adapter’s **client** (JsonRpcTransport + ProxyApiMixin) to call the MCP Proxy for tool execution; uses a separate HTTP client to call OLLAMA `/api/chat`.
  - Returns the final assistant message and optionally the full history.
- **Option B:** Implement a **standalone service** (e.g. FastAPI) that exposes one endpoint, e.g. `POST /ollama/chat`, and internally performs the same flow; this service may be built with the adapter and register with the proxy as `ollama-workstation`.
- In both cases, the **MCP Proxy URL** and **OLLAMA URL** (and model name) must be configurable (config file or environment).

### 2.4 Configuration

- **mcp_proxy_url** — base URL of the MCP Proxy (e.g. `http://localhost:3004`).
- **ollama_base_url** — base URL of OLLAMA (e.g. `http://localhost:11434`).
- **ollama_model** — default model name (e.g. `qwen3`, `llama3.1`).
- **ollama_timeout** — timeout in seconds for OLLAMA requests (optional).
- **max_tool_rounds** — maximum number of tool-call rounds per chat (optional, default e.g. 10).
- Optional: API keys or TLS settings for proxy and/or OLLAMA if required by the environment.

---

## 3. Non-functional requirements

- **Reuse:** Prefer the adapter’s existing client (e.g. `JsonRpcClient`, transport, proxy API) for MCP Proxy calls; avoid duplicating proxy protocol logic.
- **Errors:** If the proxy call fails, put the error message in the tool result content so the model can see it; do not drop the conversation.
- **Logging:** Log tool invocations (tool name, arguments, proxy response status) for debugging; no sensitive data in logs.
- **Documentation:** English; describe how to configure and run the workstation and how to call the new command (or endpoint) from the MCP Proxy.

---

## 4. Deliverables

1. **Design** — short document (or section in repo) describing the chosen option (Command vs standalone service), data flow, and config.
2. **Implementation** — code in mcp-proxy-adapter (or in a separate package that depends on it):
   - Tool schema definitions (list_servers, call_server, help) in OLLAMA-compatible format.
   - Logic: build OLLAMA chat request with tools → send to OLLAMA → on tool_calls, call MCP Proxy → append tool results → repeat.
   - Command (if Option A) registered in the adapter registry; or HTTP endpoint (if Option B).
3. **Config** — schema or example (YAML/JSON/env) for proxy URL, OLLAMA URL, model, timeouts.
4. **Example** — minimal script or request example: “send one user message to the workstation and get the model’s reply after possible tool use.”

---

## 5. Glossary

- **OLLAMA workstation** — the component (command or service) that lets OLLAMA use the MCP Proxy by injecting proxy tools into chat and executing tool_calls via the proxy.
- **MCP Proxy** — the external proxy (e.g. user-MCP-Proxy-2) that exposes `list_servers`, `call_server`, `help`, etc., and routes calls to registered servers.
- **Tool (OLLAMA)** — a function description (name, description, parameters) passed in `/api/chat`; the model may return `tool_calls` that the application must execute and then return results in a tool message.

---

## 6. Integration with mcp-proxy-adapter (reference)

This section summarizes patterns from the **mcp-proxy-adapter** package (e.g. 6.9.x) for implementing the OLLAMA workstation as an adapter Command or as a service that uses the adapter’s client. Use it to align initialization, command registration, and proxy calls.

### 6.1 Package entry points

- **Application:** `create_app(title, description, version, app_config, config_path)` — returns a FastAPI app. Config is a dictionary; `config_path` is optional.
- **Commands:** `Command` (base class), `CommandResult`, `SuccessResult`, `ErrorResult` from `mcp_proxy_adapter.commands.base` and `mcp_proxy_adapter.commands.result`.
- **Registry:** `registry` from `mcp_proxy_adapter.commands.command_registry` — singleton `CommandRegistry`. Register with `registry.register(CommandClass, "custom")` (or `"builtin"`, `"loaded"`).
- **Client:** `JsonRpcClient` from `mcp_proxy_adapter.client.jsonrpc_client` — async client that includes `CommandApiMixin` and `ProxyApiMixin`. Use it to call an MCP Proxy Adapter server (JSON-RPC) or to talk to the external MCP Proxy (if it exposes a compatible or documentable API).

### 6.2 Command class contract

- Subclass `Command`; set class attributes: `name` (str), `descr` (str). Optional: `use_queue` (bool), `result_class`.
- Implement `async def execute(self, **kwargs) -> CommandResult`. Return `SuccessResult(data=...)` or `ErrorResult(message=..., code=...)`.
- Implement `@classmethod get_schema(cls) -> Dict[str, Any]` — JSON Schema for parameters (`type`, `properties`, `required`, `additionalProperties` as needed). Built-in commands often use `additionalProperties: True` for proxy metadata.
- Optional: custom result subclass of `SuccessResult` with `data` dict and `@classmethod get_schema(cls)` for the result.

### 6.3 Initialization and command registration

- **Built-in commands** are registered by `register_builtin_commands(config_data=config)` (from `mcp_proxy_adapter.commands.builtin_commands`). The app factory typically calls this when creating the app.
- **Custom commands** (e.g. OLLAMA chat): register in the main process before starting the server, e.g. in a `register_all_commands()` function that imports command classes and calls `registry.register(CommandClass, "custom")`.
- **Hooks:** `register_custom_commands_hook(hook_func)` from `mcp_proxy_adapter.commands.hooks` — `hook_func(registry)` is invoked during `register_builtin_commands`, so custom commands can be registered there instead of (or in addition to) explicit registration in `main`.
- **Spawn/queue:** For commands with `use_queue=True` (run in child processes), register the command in the main process and also call `register_auto_import_module(module_path)` so the module is imported in child processes and can auto-register the command at import time.

### 6.4 Client usage (adapter server and proxy)

- **JsonRpcClient** is constructed with `protocol`, `host`, `port`, and optionally `token_header`, `token`, `cert`, `key`, `ca`, `check_hostname`, `timeout`. It talks to a **single** server (adapter or proxy).
- **Calling the adapter server (JSON-RPC):** `response = await client.jsonrpc_call(method, params)`; then `client._extract_result(response)` to get the result or raise on error. High-level: `await client.execute_command(command, params)`.
- **Calling the external MCP Proxy:** The adapter’s `ProxyApiMixin` provides `list_proxy_servers(proxy_url)` (GET to proxy’s `/list` or `/servers`) and methods for register/heartbeat/unregister. If the proxy exposes `list_servers`, `call_server`, `help` via **OpenAPI** (REST) rather than JSON-RPC, the workstation must use an HTTP client (e.g. same transport as `JsonRpcClient` or `httpx`) and map tool parameters to the proxy’s endpoints and payloads. Document the proxy API (URLs and request/response shape) in the design.
- **Reuse:** Prefer the adapter’s client and transport for proxy calls where the proxy API matches (e.g. JSON-RPC); otherwise implement a thin proxy client that uses the same config (URL, TLS, timeouts) and reuse it for all three tools.

### 6.5 Application startup sequence (example)

1. Load config (e.g. SimpleConfig or raw dict) and validate.
2. `app = create_app(..., app_config=app_config, config_path=config_path)`.
3. Register custom commands: `register_all_commands()` which calls `registry.register(OllamaChatCommand, "custom")` (and any other commands).
4. Start the server (e.g. via `ServerEngineFactory.get_engine("hypercorn")` and `engine.run_server(app, server_config)`).

Optional: register the workstation with the MCP Proxy (registration section in config) so external clients can call “chat with OLLAMA + proxy tools” via the proxy.

### 6.6 References in the adapter package

- **Examples:** `examples/full_application/main.py` (startup, config, `register_all_commands`), `examples/full_application/proxy_commands.py` (Command subclasses, schema, execute), `examples/full_application/commands/custom_echo_command.py` (simple custom command and result).
- **Registry:** `commands/command_registry.py` — `CommandRegistry`, `register()`, `_register_command()`, `get_command()`, `get_all_commands()`.
- **Client:** `client/jsonrpc_client/client.py` (facade), `transport.py` (`jsonrpc_call`, `_extract_result`), `command_api.py` (`execute_command`), `proxy_api.py` (`list_proxy_servers`, etc.).
