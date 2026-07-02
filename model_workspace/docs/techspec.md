# Technical specification: Model workspace

**Author:** Vasiliy Zdanovskiy  
**Email:** vasilyvz@gmail.com  

This document describes **only the model workspace** application: its role, tools, chat flow, and configuration. It does not describe Redis, MWPS, or the MCP proxy in detail; those are separate components (redis_adapter, mwps_adapter, proxy). See [ТЗ.md](ТЗ.md) and root [SPEC](../../docs/plans/refactoring_adapter_structure/SPEC.md) for the five subprojects (incl. provider clients); Model Workplace Server = one provider.

---

## 1. Purpose and scope

### 1.1 Purpose

The **model workspace** is the component that:

- Accepts chat requests (e.g. from the MCP proxy or a direct client).
- Builds **context** (system, history, relevance slot, current message) and sends a **chat request** to the model via a **provider client** (e.g. **mwps_provider_client**). **For the model workspace, Model Workplace Server server is just a separate provider** (SPEC §5).
- Injects **MCP Proxy tools** (list_servers, call_server, help) into each request so the model can discover and call servers registered in the proxy.
- When the model returns **tool calls**, the workspace executes them via the **MCP Proxy client** and appends tool results to the conversation, then continues the chat until the model replies without tool_calls or a maximum round count is reached.
- Returns the final assistant message (and optionally full history) to the caller.

So: the workspace **orchestrates** the model (via provider clients such as mwps_provider_client) and the proxy (via proxy client). It has **no** Redis or Model Workplace Server inside; it uses **mwps_provider_client** and **redis_provider_client** (SPEC §4, §5, §8).

**Role of the model:** The model is used **as the agent's tool** (e.g. by Cursor). For long dialogue, the model needs **relevant context** — not only the last N messages, but also past turns that are **semantically relevant**. Therefore **embedding service** and **relevance slot** (see [context_formation.md](context_formation.md)) are essential for the workspace.

### 1.2 Scope

- **In scope:** Design and implementation of the workspace: (1) context building, (2) calling **provider clients** (e.g. mwps_provider_client for chat/embed), (3) injecting proxy tools into requests, (4) handling tool_calls via the proxy client, (5) configuration (proxy URL, provider_clients config, model name, limits). Documentation and a minimal example.
- **Out of scope:** Implementation of redis_adapter, mwps_adapter, mwps_provider_client, redis_provider_client, or MCP proxy; modifying Redis or Model Workplace Server. Other backends are supported via their provider client packages and config.

### 1.3 Goals

1. The model (reached via **provider client**, e.g. mwps_provider_client) can **list** servers and **call** commands on any server registered in the MCP Proxy (via proxy client).
2. Single place of configuration for the **workspace**: MCP Proxy URL, provider_clients config (Model Workplace Server = one provider), default model, timeouts, context limits.
3. Context formation (segments, limits, relevance slot) is deterministic and documented; see [context_formation.md](context_formation.md).

---

## 2. Functional requirements

### 2.1 Tools exposed to the model

The workspace injects the following tools into every relevant chat request. They are implemented by calling the **MCP Proxy** (via the workspace’s proxy client).

| Tool name       | Description (for model) | Proxy call |
|-----------------|--------------------------|------------|
| **list_servers** | List servers registered in the MCP Proxy (optionally filtered). | MCP Proxy `list_servers`. |
| **call_server**  | Execute a command on a registered server. | MCP Proxy `call_server`. |
| **help**         | Get help/usage for a server or a specific command. | MCP Proxy `help`. |

Additional proxy tools may be added later; the above three are mandatory for a minimal workstation.

### 2.2 Chat flow (workspace perspective)

1. Client (or adapter command) sends a chat request to the **model workspace**.
2. The workspace builds **context** (see [context_formation.md](context_formation.md)), then builds a chat request for the **provider client** (e.g. mwps_provider_client) with: `model`, `messages`, optional `stream`, and `tools` = list_servers, call_server, help in the provider’s format.
3. The **provider client** returns a message that may contain `tool_calls`.
4. For each tool call, the workspace **calls the MCP Proxy** (via proxy client), obtains the result, and appends a tool message to the conversation.
5. Repeat from step 2 until the model returns no `tool_calls` or `max_tool_rounds` is reached.
6. The workspace returns the final assistant message (and optionally full history) to the caller.

### 2.3 Configuration (workspace)

- **mcp_proxy_url** — base URL of the MCP Proxy (e.g. `http://localhost:3004`).
- **provider_clients** — config for each provider (Model Workplace Server = one provider; connection to mwps-adapter or Model Workplace Server, model name, timeouts); see root [provider_client_config_standard](../../docs/standards/provider_client_config_standard.md).
- **mwps_model** (or default model key) — default model name for chat.
- **mwps_timeout** — timeout in seconds for chat requests (optional).
- **max_tool_rounds** — maximum tool-call rounds per chat (optional, default e.g. 10).
- Context parameters — see [context_formation.md](context_formation.md) (max_context_tokens, last_n_messages, min_semantic_tokens, etc.).

No hardcoded URLs or credentials; config from file or environment.

---

## 3. Non-functional requirements

- **Reuse:** Use the same proxy client for MCP Proxy calls; use **provider clients** (mwps_provider_client, redis_provider_client) for chat/embed and storage; do not duplicate adapter or proxy protocol in the workspace.
- **Errors:** If a proxy or adapter call fails, put the error in the tool result content (or return a structured error) so the caller or model can see it; do not drop the conversation silently.
- **Logging:** Log tool invocations and high-level flow for debugging; no secrets in logs.
- **Documentation:** English; describe how to configure and run the workspace and how to call the chat command (or endpoint) from the MCP Proxy.

---

## 4. Deliverables (workspace)

1. **Design** — short document describing data flow (workspace → provider client, workspace → proxy client), config, and command/endpoint; see [design.md](design.md).
2. **Implementation** — workspace code: context building, chat flow, tool definitions, proxy client usage, provider client usage. Command or HTTP endpoint that accepts messages and returns the final reply.
3. **Config** — schema or example for workspace config (proxy URL, provider client config, model, timeouts, context limits).
4. **Example** — minimal script or request: send one user message to the workspace and get the model’s reply after possible tool use.

---

## 5. Glossary

- **Model workspace** — the application that orchestrates the model (via provider clients) and the MCP Proxy (via proxy client), builds context, and handles tool_calls (SPEC §4). **Model Workplace Server is just one provider** for the workspace.
- **Provider client** — package that implements the uniform API (chat, embed, healthcheck, errors) for one provider; e.g. **mwps_provider_client** (Model Workplace Server), **redis_provider_client** (storage). See root [provider_client_standard](../../docs/standards/provider_client_standard.md) and [SPEC §5, §8](../../docs/plans/refactoring_adapter_structure/SPEC.md).
- **MCP Proxy** — external proxy that exposes list_servers, call_server, help and routes calls to registered servers.
- **Tool (for the model)** — function description (name, description, parameters) passed in the chat request; the model may return tool_calls that the workspace executes via the proxy client and then returns as tool messages.
