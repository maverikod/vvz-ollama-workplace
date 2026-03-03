<!--
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
-->

# Step 12: Ollama-Server Full MCP Tool Surface

## Target file

- Adapter/server implementation that registers as `ollama-server` with the proxy. Server ID and scope: [SCOPE_FREEZE.md](SCOPE_FREEZE.md) § Canonical provider names and target server IDs; implementation: [SCOPE_FREEZE.md](SCOPE_FREEZE.md) § Adapter server implementation.

## Dependencies

- [SCOPE_FREEZE.md](SCOPE_FREEZE.md)
- [../QUALITY_GATE.md](../QUALITY_GATE.md)
- [../CLIENT_UNIFICATION_TZ.md](../CLIENT_UNIFICATION_TZ.md) (FR-1, AR-2)

## Detailed scope

- Ensure `ollama-server` is an adapter-based MCP server registered in proxy, exposing **full** Ollama domain API used in production (e.g. chat, embed, list, pull).
- Publish complete command catalog; each command has strict JSON Schema parameters.
- Tool-level auth/TLS aligned with proxy mTLS policy.
- Model’s tool access to Ollama capabilities only via MCP tool calls to ollama-server.

## Success metric

- ollama-server is proxy-registered and command-discoverable (e.g. via list_servers / help).
- Command set covers agreed Ollama backend API surface; parameters use strict JSON Schema.
- Integration test or manual check: call_server(ollama-server, command, params) succeeds for key commands with real backend.

## Blocking protocol (mandatory)

- If any requirement is unclear, contradictory, or underspecified: **STOP** implementation.
- Ask a clarifying question and proceed only after explicit clarification.
