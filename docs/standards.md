# Project standards (OLLAMA workstation)

**Author:** Vasiliy Zdanovskiy  
**Email:** vasilyvz@gmail.com  

Standards derived from the technical specification and project rules. Apply these when implementing the OLLAMA interface for MCP-Proxy-Adapter.

---

## 1. Tool definitions (OLLAMA)

### 1.1 Format

- Tools exposed to OLLAMA MUST use the OLLAMA-compatible format:
  `{ "type": "function", "function": { "name", "description", "parameters" } }`.
- `parameters` MUST be a JSON Schema object (e.g. `type`, `properties`, `required`).

### 1.2 Mandatory tools

| Tool          | Purpose                         | Implementation        |
|---------------|---------------------------------|------------------------|
| `list_servers`| List servers in MCP Proxy       | MCP Proxy `list_servers` (or equivalent) |
| `call_server` | Execute command on a server     | MCP Proxy `call_server`                  |
| `help`        | Get help for server/command     | MCP Proxy `help`                        |

Additional proxy tools (e.g. `health_check`, `network_check`) may be added later; the three above are mandatory for the minimal workstation.

### 1.3 Parameter naming

- Use the same parameter names as the MCP Proxy API where applicable: `server_id`, `copy_number`, `command`, `params` for `call_server`; `page`, `page_size`, `filter_enabled` for `list_servers`; `server_id`, `copy_number`, `command` for `help`.

---

## 2. Configuration

### 2.1 Required settings

- **mcp_proxy_url** — base URL of the MCP Proxy (e.g. `http://localhost:3004`).
- **ollama_base_url** — base URL of OLLAMA (e.g. `http://localhost:11434`).
- **ollama_model** — default model name (e.g. `qwen3`, `llama3.1`).

### 2.2 Optional settings

- **ollama_timeout** — timeout in seconds for OLLAMA requests.
- **max_tool_rounds** — maximum tool-call rounds per chat (default e.g. 10).
- API keys or TLS settings for proxy and/or OLLAMA if required by the environment.

### 2.3 Config source

- Single place of configuration: config file (YAML/JSON) or environment variables.
- No hardcoded URLs or credentials in code.

### 2.4 Model context: which commands the model sees

- **Only commands specified in config** may appear in the model context. The config section `ollama_workstation` defines:
  - **allowed_commands** — list of command IDs (e.g. `echo.ollama-adapter`) permitted for the model.
  - **forbidden_commands** — list always excluded.
  - **commands_policy** — `deny_by_default` (only allowed_commands) or `allow_by_default` (all discovered minus forbidden; if allowed_commands is set, intersection is used).
- When `allowed_commands` / `forbidden_commands` / `commands_policy` are absent, the default is **deny_by_default** with empty allowed (the model sees no tools until the config lists them).
- **Session** applies an additional filter: from the config-permitted set, only commands in the session’s **allowed_commands** (if set) and not in the session’s **forbidden_commands** are sent to the model.
- Order: (1) config policy → (2) session allowed/forbidden → (3) vectorization rules if applicable.
- **Help for the model:** The **help** tool is always present in the tool list (even when no other tools are available). Called with no parameters, it returns a short reference in English on the order and way of using tools, the format for calling commands, and how to get help for a specific command. Called with `command_name` (e.g. `echo`, `embed_execute`), it returns the full description and parameters from the server that provides that command.

---

## 3. Errors and resilience

- If a proxy call fails, put the **error message in the tool result content** so the model can see it; do not drop the conversation.
- Do not leave the conversation in an inconsistent state; always append a tool message (success or error) and continue or terminate within `max_tool_rounds`.

---

## 4. Logging

- Log tool invocations: tool name, arguments (no secrets), proxy response status for debugging.
- No sensitive data (tokens, keys, full message bodies) in logs.
- Use structured logging where applicable; follow project log-importance rules (0–10) if defined.

---

## 5. Reuse and dependencies

- **Reuse:** Prefer the adapter’s existing client (e.g. `JsonRpcClient`, transport, proxy API) for MCP Proxy calls; avoid duplicating proxy protocol logic.
- If the proxy exposes a different API (e.g. OpenAPI REST), use a minimal HTTP client and document the mapping from tool parameters to proxy requests.

---

## 6. Documentation and language

- **Documentation:** English (unless the product owner explicitly requests another language).
- **Code, comments, docstrings, tests:** English only.
- Describe how to configure and run the workstation and how to call the new command (or endpoint) from the MCP Proxy.

---

## 7. embed-client and svo-client (WebSocket / event API only)

- **Dependencies:** `embed-client>=3.1.7.24`, `svo-client>=2.2.15`. Both communicate over WebSocket where supported.
- **Rule:** Use **bidirectional event interfaces** only. Do **not** use legacy polling.
  - **embed-client:** Prefer `AdapterTransport.execute_async(command, params, on_result=..., timeout=...)` (result via WebSocket callback) or `wait_for_job_via_websocket(job_id, timeout)`; use `open_bidirectional_ws_channel()` when you need a long-lived send/receive channel. Do **not** use `execute_command_unified(..., auto_poll=True)` or `wait_for_job_poll` for embed flows.
  - **svo-client:** Use `ChunkerClient.chunk(...)` which uses the adapter’s WebSocket path (`execute_command_unified` + `/ws`). For custom flows use `open_ws_channel()` (bidirectional). Do **not** use polling-only patterns.
- **Rationale:** Polling can cause high latency and timeouts; event/WebSocket is the supported, low-latency path.

---

## 8. Code quality

- File header docstring: Author (Vasiliy Zdanovskiy), email (vasilyvz@gmail.com).
- One class per file (except small exceptions/enums); split files when they exceed 350–400 lines.
- After each change: run black, flake8, mypy; fix all issues. Run code_mapper after each batch of file changes.
- No `pass` instead of implementation in production code; use `NotImplemented` only in abstract methods.

---

## 9. Project layout rules

- **docs/** — Documentation and guides (документация и руководства). Hand-written specs, standards, how-tos, reference docs.
- **docs/reports/** — AI reports (отчёты ИИ). All AI-generated reports, analyses, or run summaries go here; do not use this folder for hand-written documentation.
- **docs/plans/** — Plans (планы). Implementation plans, cleanup plans, roadmaps.

---

## 10. Deliverables alignment

- **Design:** Short document describing chosen option (Command vs standalone service), data flow, and config.
- **Implementation:** Tool schemas in OLLAMA format; chat flow (request with tools → OLLAMA → tool_calls → proxy → tool results → repeat); Command or HTTP endpoint; config schema or example.
- **Example:** Minimal script or request example: one user message to the workstation, model reply after possible tool use.
