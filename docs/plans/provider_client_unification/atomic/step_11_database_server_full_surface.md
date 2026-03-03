<!--
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
-->

# Step 11: Database-Server Full MCP Tool Surface

## Target file

- Adapter/server implementation that registers as `database-server` with the proxy. Server ID and scope: [SCOPE_FREEZE.md](SCOPE_FREEZE.md) § Canonical provider names and target server IDs; implementation: [SCOPE_FREEZE.md](SCOPE_FREEZE.md) § Adapter server implementation.

## Dependencies

- [SCOPE_FREEZE.md](SCOPE_FREEZE.md)
- [../QUALITY_GATE.md](../QUALITY_GATE.md)
- [../CLIENT_UNIFICATION_TZ.md](../CLIENT_UNIFICATION_TZ.md) (FR-1, AR-2)

## Detailed scope

- Ensure `database-server` is an adapter-based MCP server registered in proxy, exposing **full** Redis domain API used in production.
- Publish complete command catalog; each command has strict JSON Schema parameters.
- Tool-level auth/TLS aligned with proxy mTLS policy.
- No direct workstation → redis; model uses only MCP tool calls to database-server.

## Success metric

- database-server is proxy-registered and command-discoverable (e.g. via list_servers / help).
- Command set covers agreed Redis backend API surface; parameters use strict JSON Schema.
- Integration test or manual check: call_server(database-server, command, params) succeeds for key commands with real backend.

## Implemented artifacts

- **Command catalog:** [DATABASE_SERVER_COMMAND_CATALOG.md](DATABASE_SERVER_COMMAND_CATALOG.md) — agreed Redis API surface (message_write, messages_get_by_session, session_get, session_create, session_update) with strict JSON Schema.
- **Config:** `database_server.storage.backend` may be `redis`; when redis: `redis_host`, `redis_port` (optional `redis_password`, `message_key_prefix`, `session_key_prefix`) in `src/database_server/config_validator.py` and `config_generator.py`.
- **Commands:** `src/database_server/commands/` — adapter Command classes; `register_database_commands(registry)` in `src/database_server/commands/__init__.py`.
- **Runner:** `docker/run_adapter.py` — when `registration.server_id == "database-server"` loads config, validates with `validate_database_server_config`, creates app with Database Server title/description, registers only database commands, starts server (no model loading).

## Blocking protocol (mandatory)

- If any requirement is unclear, contradictory, or underspecified: **STOP** implementation.
- Ask a clarifying question and proceed only after explicit clarification.
