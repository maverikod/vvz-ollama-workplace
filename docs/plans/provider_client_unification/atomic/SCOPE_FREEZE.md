<!--
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
-->

# Scope Freeze and Boundary — Provider Client Unification Plan

This document fixes scope, canonical names, target paths, and out-of-scope boundaries for the atomic steps 01–13. All step files must reference this document where applicable; no placeholder naming remains in step files after step_00.

References: [CLIENT_UNIFICATION_TZ.md](../CLIENT_UNIFICATION_TZ.md), [QUALITY_GATE.md](../QUALITY_GATE.md), [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).

---

## 1. Canonical provider names and target server IDs

- **Provider names** (config key and registry): use lowercase, hyphen-free identifiers. Phase 1 in-scope: `ollama`. Optional for phase 1 (documented, not mandatory to implement in steps 01–13): `openai`, `anthropic`, `google`, `xai`, `deepseek`.
- **Target MCP server IDs** (adapter facades registered in proxy):
  - `database-server` — Redis domain operations.
  - `ollama-server` — Ollama domain operations.

These IDs are fixed for this plan; steps 11 and 12 implement full tool surface for `database-server` and `ollama-server` respectively.

---

## 2. In-scope provider clients (phase 1)

- **Ollama** — mandatory. Implemented as first-class provider client (step_08); contract from client standard and abstract base; no direct workstation → raw Ollama in runtime.
- **Other providers** (openai, anthropic, google, xai, deepseek) — optional for phase 1. Config standard and schema support them; concrete clients may be added in a later plan. This plan does not require implementing any non-Ollama provider client.

---

## 3. Target paths (canonical)

All paths are relative to project root.

| Artifact | Canonical path |
|----------|----------------|
| Provider client errors | `src/ollama_workstation/provider_errors.py` |
| Abstract base class | `src/ollama_workstation/provider_client_base.py` |
| Provider client config schema | `src/ollama_workstation/provider_client_config_schema.py` |
| Provider client config validator | `src/ollama_workstation/provider_client_config_validator.py` |
| Provider client config generator | `src/ollama_workstation/provider_client_config_generator.py` |
| Ollama provider client | `src/ollama_workstation/ollama_provider_client.py` |
| Provider client registry | `src/ollama_workstation/provider_registry.py` |
| Client standard (normative doc) | `docs/standards/provider_client_standard.md` |
| Config standard (normative doc) | `docs/standards/provider_client_config_standard.md` |
| Integration tests | `tests/integration/test_provider_client_unification.py` (may be split into several files if needed) |

**Ollama migration:** Existing Ollama usage may be refactored so that the workstation uses `ollama_provider_client.py` only; `ollama_client.py` may be replaced or reduced to internal use by the Ollama provider client, as agreed in step_08. No long-term compatibility shim between old and new paths (see Greenfield policy below).

---

## 4. Out-of-scope for this plan

- **Replacing or redesigning MCP Proxy itself** — proxy is used as-is; only adapter servers and workstation→proxy usage are in scope.
- **Changing external provider APIs** — no changes to third-party provider HTTP/API contracts.
- **Product UI/UX changes** — no user-facing UI/UX work.
- **Legacy direct-access runtime paths** — no preservation of workstation → raw redis or workstation → raw ollama for compatibility (see Greenfield policy).
- **Long-term compatibility shims** — no code paths that keep old and new interfaces in parallel indefinitely; migration-only toggles only if time-limited and explicitly documented for removal (per TZ).
- **Implementing concrete provider clients other than Ollama** in steps 01–13 — config/schema/registry support other names, but only Ollama client is delivered in this plan.

---

## 5. Embed contract (from TZ)

- **Method `embed(request)` is mandatory** for all provider clients; every client must implement it.
- If the provider does not support embeddings:
  - Set **`supports_embeddings = False`** (or equivalent capability flag).
  - Implement **`embed(request)`** so that when called, it raises a **single, well-defined error** (e.g. `CapabilityNotSupportedError` or a documented subtype of `ValidationError` from `provider_errors.py`), without performing any network call.
- Workstation must check `supports_embeddings` before calling `embed`. If it calls `embed` on a client that reported `supports_embeddings=False`, the client’s raising the defined error is acceptable and correct.
- **Not allowed:** capability flag only without implementing `embed` — the method must always be present; unsupported embeddings = flag + defined error on call.

---

## 6. Greenfield policy (from TZ)

- **No legacy direct-access runtime paths** — do not preserve workstation → raw redis or workstation → raw ollama for compatibility.
- **No long-term compatibility shims** — do not add shims that keep old and new runtime paths in parallel indefinitely.
- Prefer **clean replacement** of outdated interfaces over staged long-term coexistence.
- Migration-only compatibility toggles only if **time-limited** and **explicitly documented for removal**.

---

## 7. Step index (for reference)

| Step | File | Uses SCOPE_FREEZE for |
|------|------|------------------------|
| 01 | step_01_client_standard_document.md | Target path (docs), embed contract, error categories |
| 02 | step_02_config_standard_document.md | Target path (docs), provider names |
| 03 | step_03_uniform_error_model.md | Target path (provider_errors.py) |
| 04 | step_04_abstract_base_class.md | Target path (provider_client_base.py), embed contract |
| 05 | step_05_provider_client_config_schema.md | Target path (schema module) |
| 06 | step_06_provider_client_config_validator.md | Target path (validator), startup behaviour |
| 07 | step_07_provider_client_config_generator.md | Target path (generator) |
| 08 | step_08_ollama_provider_client.md | Target path (ollama_provider_client), migration of ollama_client |
| 09 | step_09_provider_client_registry.md | Provider names, config layout |
| 10 | step_10_workstation_orchestration_refactor.md | Allowed/forbidden paths, server IDs |
| 11 | step_11_database_server_full_surface.md | Server ID `database-server` |
| 12 | step_12_ollama_server_full_surface.md | Server ID `ollama-server` |
| 13 | step_13_integration_tests.md | Target path (tests), no-direct-access, server IDs |

---

## 8. Step_10: modules touched (workstation refactor)

Modules that may be changed to remove direct redis/ollama access and to use provider clients only:

- `src/ollama_workstation/chat_flow.py` — model communication flow.
- Config loading that wires provider clients (e.g. in `config.py` or equivalent).
- Any other module that currently performs model communication or direct redis/ollama access; exact list to be confirmed during step_10.

---

## 9. Adapter server implementation (steps 11–12)

Target server IDs are fixed: `database-server`, `ollama-server`. The **implementation** of the adapter/server that registers with the proxy may live in the adapter codebase or in a project adapter wrapper; no single canonical file path is fixed in this plan. Steps 11 and 12 require that the corresponding server is proxy-registered with full command catalog and strict JSON Schema parameters.

---

## 10. Startup validation

Provider client config validation (step_06) must run before runtime; invalid config must block startup. Integration with workstation startup (fail fast on validation error) is expected (see step_10).
