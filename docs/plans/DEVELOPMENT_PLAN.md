# Step-by-step development plan: OLLAMA workstation

**Author:** Vasiliy Zdanovskiy  
**Email:** vasilyvz@gmail.com  

Plan aligned with [../techspec.md](../techspec.md) and mcp-proxy-adapter capabilities. One step = one file; each step describes the single code file to create or modify.

---

## Adapter reference (summary)

### Initialization and command registration

- **App:** `create_app(title, description, version, app_config, config_path)` returns FastAPI app. Built-in commands are registered inside the app factory via `register_builtin_commands(config_data)`.
- **Custom commands:** Register in the main process before starting the server: `registry.register(CommandClass, "custom")` (e.g. in `register_all_commands()`). Use `registry` from `mcp_proxy_adapter.commands.command_registry`.
- **Hooks:** `register_custom_commands_hook(hook_func)` from `mcp_proxy_adapter.commands.hooks`; `hook_func(registry)` is called during `register_builtin_commands`, so custom commands can be registered there instead of in `main`.

### Command shape and metadata (not less detailed than man)

- **Class attributes:** `name` (str), `descr` (str). Optional: `version`, `category`, `author`, `email`, `result_class`, `use_queue`.
- **get_schema():** Must return a JSON Schema dict: `type: "object"`, `properties` (each property with `type` and `description`), `required` list, top-level `description`. For discoverability (help/man-like): include an `examples` array of `{ "command": "<name>", "params": {...}, "description": "..." }`. Use `additionalProperties: True` only if proxy routing metadata is required.
- **execute(self, **kwargs):** Async; returns `SuccessResult(data=...)` or `ErrorResult(message=..., code=...)`. Parameters must match schema; optional `context` is injected by the adapter.
- **Result:** Optional custom result class (subclass of `SuccessResult`) with `get_schema()` for the result shape.

### Command schema (adapter contract)

- Schema is used for: (1) parameter validation before `execute`, (2) OpenAPI/help output, (3) client discovery. So each parameter should have a clear `description`; the schema root should have a `description` summarizing the command.

### Client and adapter responsibilities

- **JsonRpcClient:** Construct with `protocol`, `host`, `port`, and optionally `token_header`, `token`, `cert`, `key`, `ca`, `check_hostname`, `timeout`. Transport adds `Content-Type: application/json` and auth header when token is set. Calls: `await client.jsonrpc_call(method, params)` (POST to `base_url/api/jsonrpc`) or `await client.execute_command(command, params)`.
- **Adapter request/response:** The adapter receives HTTP at `/api/jsonrpc`, applies security middleware (e.g. API key / Bearer), parses JSON-RPC, resolves the command from the registry, validates params with the command’s schema, runs `command.execute(**params, context=context)`, and returns the result as JSON-RPC `result` or `error`. The command implementation does not handle HTTP or auth; it only receives validated params and returns a `CommandResult`.

---

## Step-by-step plan (one file per step)

### Step 1 — `src/ollama_workstation/__init__.py`

**Purpose:** Package root. Export public names: config loader, tool definitions, chat flow, proxy client, and the ollama_chat command class (so that the app can `from ollama_workstation import ...` and register the command). No business logic; only imports and `__all__`.

---

### Step 2 — `src/ollama_workstation/config.py`

**Purpose:** Load and expose workstation configuration. Fields: `mcp_proxy_url`, `ollama_base_url`, `ollama_model`, `ollama_timeout` (optional), `max_tool_rounds` (optional, default 10). Source: config file (YAML/JSON) or environment variables; single place, no hardcoded URLs or credentials. Expose a small dataclass or similar and a function to load it (e.g. `load_config(path?) -> WorkstationConfig`). Used by proxy client, chat flow, and command.

---

### Step 3 — `src/ollama_workstation/tools.py`

**Purpose:** OLLAMA tool definitions. Provide a list (or builder) of tools in OLLAMA format: `{ "type": "function", "function": { "name", "description", "parameters" } }`. Three mandatory tools: `list_servers` (params: `page`, `page_size`, `filter_enabled`), `call_server` (params: `server_id`, `copy_number`, `command`, `params`), `help` (params: `server_id`, `copy_number`, `command`). Each `parameters` must be a full JSON Schema object (type, properties with descriptions, required). Descriptions must be clear enough for the model (man-like). No execution logic here; only definitions.

---

### Step 4 — `src/ollama_workstation/proxy_client.py`

**Purpose:** Thin client that calls the MCP Proxy for the three tools. Use the adapter’s `JsonRpcClient` (or HTTP client) configured from workstation config (proxy URL, TLS, timeout). Implement three methods: `list_servers(page?, page_size?, filter_enabled?)`, `call_server(server_id, command, copy_number?, params?)`, `help(server_id, copy_number?, command?)`. Map arguments to the proxy API (JSON-RPC or OpenAPI as documented). On failure, raise or return a structured error so the chat flow can put the error message into the tool result content. No OLLAMA calls here.

---

### Step 5 — `src/ollama_workstation/chat_flow.py`

**Purpose:** Core chat loop. Input: config, messages list, optional model, stream flag, max_tool_rounds. Logic: (1) Build OLLAMA request to `/api/chat` with `model`, `messages`, `tools` (from `tools.py`), optional `stream`. (2) Send request to OLLAMA (HTTP client using `ollama_base_url`, `ollama_timeout`). (3) If the response contains `tool_calls`, for each call invoke `proxy_client.list_servers` / `call_server` / `help` as appropriate, then append a tool message in the format required by OLLAMA (e.g. `{ "role": "tool", "tool_name": "<name>", "content": "<result>" }` per ТЗ 2.2; on proxy error put the error message in `content`, do not drop the conversation). (4) Repeat until the model returns no tool_calls or `max_tool_rounds` is reached. (5) Return the final assistant message and optionally the full message history. **Logging (ТЗ 3):** log each tool invocation (tool name, arguments without secrets, proxy response status); no sensitive data in logs.

---

### Step 6 — `src/ollama_workstation/commands/__init__.py`

**Purpose:** Commands subpackage. Export `OllamaChatCommand` (and any other commands in this package). Used by the main app to register commands.

---

### Step 7 — `src/ollama_workstation/commands/ollama_chat_command.py`

**Purpose:** Adapter Command implementation. Class name e.g. `OllamaChatCommand`. Attributes: `name = "ollama_chat"` (or `ollama_chat_with_proxy_tools`), `descr` with a full one-paragraph description (man-like). `get_schema()`: JSON Schema with `messages` (array, required), `model` (string, optional), `stream` (boolean, optional), `max_tool_rounds` (integer, optional); root `description` and per-property `description`; optionally `examples` array. `execute(self, messages, model=None, stream=False, max_tool_rounds=None, **kwargs)` loads config, runs the chat flow from `chat_flow.py`, returns `SuccessResult(data={ "message": final_assistant_message, "history": ... })` or `ErrorResult(message=..., code=...)`. Use the adapter’s client only for proxy calls; use a separate HTTP client for OLLAMA. No auth logic inside the command; the adapter handles request/auth.

---

### Step 8 — `src/ollama_workstation/registration.py`

**Purpose:** Single place that registers the workstation command with the adapter registry. Function e.g. `register_ollama_workstation(registry)` that calls `registry.register(OllamaChatCommand, "custom")`. The main app (or a custom-commands hook) will call this so that `ollama_chat` is available via JSON-RPC.

---

### Step 9 — `config/ollama_workstation.example.yaml` (or `.json`)

**Purpose:** Example configuration file (ТЗ 4 Deliverable 3: config schema or example). Contains `mcp_proxy_url`, `ollama_base_url`, `ollama_model`, optional `ollama_timeout`, `max_tool_rounds`. Optional placeholders for API keys or TLS paths for proxy and/or OLLAMA. Documented so users can copy and adjust. Optionally add a JSON Schema for the config (same folder or in docs) so the example doubles as the schema reference. No code.

---

### Step 10 — `examples/ollama_chat_example.py`

**Purpose:** Minimal runnable example: load config, create a JsonRpcClient (or HTTP client) pointing at the adapter server, send one user message to the `ollama_chat` command (e.g. “List available servers”), and print the model’s reply (after any tool use). Shows how to call the workstation from a client. Requires the server to be running with the workstation command registered.

---

### Step 11 — `tests/unit/test_tools.py`

**Purpose:** Unit tests for `tools.py`: check that the list of tools contains exactly the three required tools, that each has `type`, `function`, `name`, `description`, `parameters` (valid JSON Schema), and that parameter names match the tech spec.

---

### Step 12 — `tests/unit/test_config.py`

**Purpose:** Unit tests for `config.py`: load config from a fixture file and from environment; assert that all required and optional fields are read correctly and that defaults (e.g. `max_tool_rounds`) apply.

---

### Step 13 — `tests/unit/test_proxy_client.py`

**Purpose:** Unit tests for `proxy_client.py` with a mocked HTTP/JsonRpc client: assert that `list_servers`, `call_server`, and `help` are called with the correct URLs/payloads and that errors are surfaced as expected.

---

### Step 14 — `tests/unit/test_chat_flow.py`

**Purpose:** Unit tests for `chat_flow.py` with mocked OLLAMA and proxy client: e.g. one round without tool_calls, one round with tool_calls and tool results, and one with proxy error (error message in tool content). Assert final message and history shape.

---

### Step 15 — `tests/unit/test_ollama_chat_command.py`

**Purpose:** Unit tests for `OllamaChatCommand`: schema shape and required/optional params; execute with mocked chat_flow returns success or error and the result structure (e.g. `data.message`, `data.history`).

---

### Step 16 — `docs/design.md` (optional but recommended)

**Purpose:** Short design document (ТЗ 4 Deliverable 1): chosen option (Option A — adapter Command), data flow diagram (text or Mermaid), config mapping, and how the proxy API (list_servers, call_server, help) is invoked. Reference for maintainers and for aligning with tech spec section 4 (Deliverables).

---

### Step 17 — Optional: registration of workstation with MCP Proxy (ТЗ 1.2)

**Purpose:** ТЗ 1.2 in scope: “optionally registers itself with the MCP Proxy so that external clients can ‘chat with OLLAMA + MCP tools’ via the proxy.” This is **optional**. Options: (a) Document in **design.md** how to enable the adapter’s existing proxy registration (e.g. `registration` / `proxy_client` section in app config) so that the server that runs the `ollama_chat` command registers with the MCP Proxy; then external clients call the proxy, which routes to this server and thus to `ollama_chat`. (b) Or add a small module or config section that, when enabled, triggers registration of the current server (URL where the adapter is running) with the proxy at startup. No separate code file is mandatory if (a) is enough; then Step 17 is “Describe in design.md and, if needed, in example config.” If (b) is implemented, add one file (e.g. `src/ollama_workstation/proxy_registration.py` or integration in an existing startup script) and document it in design.md.

---

## Compliance with tech spec (checklist)

| ТЗ section | Requirement | Plan coverage |
|------------|-------------|---------------|
| 1.2 Scope (4) | Optionally register workstation with MCP Proxy so external clients can call “chat with OLLAMA + MCP tools” via proxy | **Step 17** (see below): document optional proxy registration; design.md describes config for adapter registration. |
| 2.1 Tools | list_servers, call_server, help with exact params | Step 3 ✓ |
| 2.2 Chat flow | Request to OLLAMA with model, messages, tools; on tool_calls call proxy, append tool message; repeat; return final + history | Step 5 ✓. **Explicit:** tool message format `role: "tool"`, `tool_name`, `content` (per ТЗ 2.2 step 4). |
| 2.3 Option A | Command: messages, model, stream, max_tool_rounds; adapter client for proxy, separate HTTP for OLLAMA; return final message and optionally history | Step 7 ✓ |
| 2.4 Config | mcp_proxy_url, ollama_base_url, ollama_model, ollama_timeout, max_tool_rounds; optional API keys/TLS | Step 2, 9 ✓ |
| 3 NFR Errors | Proxy failure → error in tool result content; do not drop conversation | Step 5 ✓ |
| 3 NFR Logging | Log tool invocations (tool name, arguments, proxy response status); no sensitive data | **Step 5:** chat_flow must log tool name, arguments (no secrets), proxy response status. |
| 3 NFR Reuse | Prefer adapter client for proxy calls | Step 4 ✓ |
| 3 NFR Documentation | English; how to configure, run, and call command from MCP Proxy | Step 16, 10 ✓ |
| 4 Deliverables | Design, Implementation (tools + flow + command), Config (schema or example), Example | Steps 16, 3–8, 9 (+ schema note), 10 ✓ |

---

## Order of implementation

Implement in order: **2 → 3 → 4 → 5 → 6, 7 → 8 → 1** (then 9, 10, 11–17). Step 1 can be filled after 6–7 so that `__init__.py` exports the command class and registration helper. Steps 9–10 and 11–16 can proceed in parallel after the core (2–8) is done.

## File count summary

| Step | File | Description |
|------|------|-------------|
| 1 | `src/ollama_workstation/__init__.py` | Package exports |
| 2 | `src/ollama_workstation/config.py` | Config model and loader |
| 3 | `src/ollama_workstation/tools.py` | OLLAMA tool definitions (3 tools) |
| 4 | `src/ollama_workstation/proxy_client.py` | MCP Proxy client (list_servers, call_server, help) |
| 5 | `src/ollama_workstation/chat_flow.py` | Chat loop with OLLAMA + tool execution |
| 6 | `src/ollama_workstation/commands/__init__.py` | Commands package |
| 7 | `src/ollama_workstation/commands/ollama_chat_command.py` | Adapter Command ollama_chat |
| 8 | `src/ollama_workstation/registration.py` | Register command with registry |
| 9 | `config/ollama_workstation.example.yaml` | Example config |
| 10 | `examples/ollama_chat_example.py` | Minimal client example |
| 11 | `tests/unit/test_tools.py` | Unit tests for tools |
| 12 | `tests/unit/test_config.py` | Unit tests for config |
| 13 | `tests/unit/test_proxy_client.py` | Unit tests for proxy client |
| 14 | `tests/unit/test_chat_flow.py` | Unit tests for chat flow |
| 15 | `tests/unit/test_ollama_chat_command.py` | Unit tests for command |
| 16 | `docs/design.md` | Design document |
| 17 | Optional: design.md + config / or `proxy_registration.py` | Optional registration of workstation with MCP Proxy (ТЗ 1.2) |
