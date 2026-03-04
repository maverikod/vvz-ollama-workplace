# redis_adapter — documentation

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

Documentation for the **redis_adapter** subproject only. Canonical plan: repository root [docs/plans/refactoring_adapter_structure/SPEC.md](../../docs/plans/refactoring_adapter_structure/SPEC.md).

---

## Technical specification (ТЗ)

**[ТЗ.md](ТЗ.md)** — technical specification for this subproject (SPEC §7): Redis adapter **client** and **server** on mcp-proxy-adapter; WebSocket transport; request/response and error classes; single `execute(command_name, *args, **kwargs)` plus wrappers (get, set, hgetall, lrange, …); validation in wrappers. Container **redis-adapter**: Redis + adapter server.

---

## Other

- **reports/** — AI-generated reports (отчёты ИИ). Do not use for hand-written docs.
- **plans/** — Implementation plans, roadmaps.
