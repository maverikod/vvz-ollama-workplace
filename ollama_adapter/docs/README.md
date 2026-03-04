# ollama_adapter — documentation

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

Documentation for the **ollama_adapter** subproject only. Canonical plan: repository root [docs/plans/refactoring_adapter_structure/SPEC.md](../../docs/plans/refactoring_adapter_structure/SPEC.md).

---

## Technical specification (ТЗ)

**[ТЗ.md](ТЗ.md)** — technical specification for this subproject (SPEC §6): Ollama adapter **client** and **server** on mcp-proxy-adapter; WebSocket transport; request/response and error classes; single `execute(method_name, **params)` plus wrappers (tags, chat, generate, embeddings, pull, push, delete, show, copy, create, ps, version); validation in wrappers. Container **ollama-adapter**: Ollama + adapter server.

---

## Other

- **reports/** — AI-generated reports (отчёты ИИ). Do not use for hand-written docs.
- **plans/** — Implementation plans, roadmaps.
