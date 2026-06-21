# redis_adapter — documentation

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

Documentation for the **redis_adapter** subproject only. Canonical plan: repository root [docs/plans/refactoring_adapter_structure/SPEC.md](../../docs/plans/refactoring_adapter_structure/SPEC.md).

---

## Technical specifications (ТЗ)

- **[ТЗ.md](ТЗ.md)** — technical specification for this subproject (SPEC §7): Redis adapter **client** and **server** on mcp-proxy-adapter; WebSocket transport; request/response and error classes; single `execute(command_name, *args, **kwargs)` plus wrappers (get, set, hgetall, lrange, …); validation in wrappers. Container **redis-adapter**: Redis + adapter server.
- **[SPEC_HIGH_LEVEL_DATABASE_API.md](SPEC_HIGH_LEVEL_DATABASE_API.md)** — high-level database API (ТЗ): project-specific domain methods (sessions, messages) on the server (database_server) and a **client on adapter + WebSocket** exposing get_session, create_session, list_sessions, get_session_with_messages, etc. See also root [docs/reports/redis_database_high_level_api_analysis.md](../../docs/reports/redis_database_high_level_api_analysis.md).

---

## Other

- **reports/** — AI-generated reports (отчёты ИИ). Do not use for hand-written docs.
- **plans/** — Implementation plans, roadmaps.
