# Naming Freeze (Phase 1)

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

## Status

Approved baseline naming for phase-1 implementation.
This document is the single source of truth for package names and scope boundaries.

## Phase-1 server/client pairs

### 1) Model Workspace pair

- Server package (source): `model_workspace_server`
- Client package (source): `model_workspace_client`
- Responsibility:
  - server: model workspace runtime and command execution surface
  - client: all network interaction to model workspace server

### 2) Database pair

- Server package (source): `database_server`
- Client package (source): `database_client`
- Responsibility:
  - server: database service contract (storage-facing service API)
  - client: all network interaction to database server

## PyPI distribution mapping (phase-1)

| Source package | PyPI distribution name |
|---|---|
| `model_workspace_client` | `model-workspace-client` |
| `database_client` | `ollama-model-database-client` |

Notes:
- Server packages are not in phase-1 PyPI publication scope.
- Client distributions are published independently.

## WS contract identifier (phase-1)

- Contract version: `ws-contract-v1`
- Compatibility policy:
  - backward compatible additions only within v1
  - breaking transport/schema changes require v2
  - fallback transport must remain explicit and documented

## Proxy registration contract (phase-1)

Registration target must be configurable for phase-1:
- Transport: `mTLS` only
- Current stage value: `https://172.28.0.2:3004`
- Production value may differ and must not require code changes.

Required config values:
- `registration.enabled = true`
- `registration.protocol = "mtls"`
- `registration.register_url = "<proxy_base_url>/register"`
- `registration.unregister_url = "<proxy_base_url>/unregister"`
- `registration.heartbeat.url = "<proxy_base_url>/proxy/heartbeat"`
- `ollama_workstation.mcp_proxy_url = "<proxy_base_url>"`

Certificate source:
- Use certificates from project directory `mtls_certificates`.
- CA path (phase-1 canonical): `mtls_certificates/ca/ca.crt`
- Client cert/key paths must reference files under `mtls_certificates/client/`.
- Server cert/key paths must reference files under `mtls_certificates/server/`.

## Explicitly out of phase-1 scope

- Additional server/client pairs beyond:
  - model workspace
  - database
- Multi-tenant plugin marketplace packaging strategy
- Cross-repo package split (phase-1 stays in monorepo with independent packages)

## Naming and import rules

- Network calls are allowed only inside corresponding client packages.
- Other modules consume typed client APIs; no ad-hoc direct transport calls.
- New pair names require explicit update of:
  - `ATOMIC_PLAN_V2.md`
  - `TRACEABILITY_MATRIX.md`
  - this file

## References

- `../QUALITY_GATE.md` — shared quality gate for every atomic step.
- `../TRACEABILITY_MATRIX.md` — requirement-to-step traceability and locked constraints.
