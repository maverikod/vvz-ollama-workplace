# Traceability Matrix: Requirements -> Atomic V2 Steps -> Verification

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

## Purpose

Provide strict traceability for Cursor Auto execution:
- requirement coverage
- implementation step links
- objective verification commands

Use together with:
- [`atomic_v2/ATOMIC_PLAN_V2.md`](./atomic_v2/ATOMIC_PLAN_V2.md)
- [`QUALITY_GATE.md`](./QUALITY_GATE.md)

## Requirement coverage matrix

| Req ID | Requirement | Covered by steps | Verification (objective) | Coverage status |
|---|---|---|---|---|
| R1 | Dedicated client per server in separate package/directory | `atomic_v2/step_01..06`, `atomic_v2/step_07..12`, `atomic_v2/step_16` | Check package layout for model-workspace and database pairs; no direct bypass calls outside dedicated clients | Covered |
| R2 | Each server has config generator + validator + full CLI | `atomic_v2/step_01..03`, `atomic_v2/step_07..09` | Run server CLI commands for both servers: `generate/validate/show-schema/sample` | Covered |
| R3 | Each client has config generator + validator + full CLI | `atomic_v2/step_04..06`, `atomic_v2/step_10..12` | Run client CLI commands for both clients: `generate/validate/show-schema/test-connection` | Covered |
| R4 | Client-server communication over WS (adapter capability) | `atomic_v2/step_13`, `atomic_v2/step_18` | Verify WS path usage in integration/log artifacts for model-workspace and database flows | Covered |
| R5 | Config/logs/cache/model-data mounted in containers | `atomic_v2/step_15` | Inspect runtime mounts and validate expected host-container mapping | Covered |
| R6 | Container user mapping `1000:1000` | `atomic_v2/step_15` | Verify runtime UID:GID via container inspection | Covered |
| R7 | Auto-attach containers to `smart-assistant` network | `atomic_v2/step_15`, `atomic_v2/step_18` | Verify all required containers present in `smart-assistant` network | Covered |
| R8 | Client packages independent and publishable on PyPI | `atomic_v2/step_16` | Build/install standalone artifacts for both client packages and perform publish dry-run | Covered |
| R9 | Correct registration + man-level metadata + strict schemas | `atomic_v2/step_14`, `atomic_v2/step_18` | Real discovery/help output contains detailed metadata and strict schema behavior; registration works via mTLS on configured `<proxy_base_url>` with certs from `mtls_certificates` | Covered |
| R10 | Final testing on real servers (no mocks) | `atomic_v2/step_17`, `atomic_v2/step_18` | E2E runs on real services only; no mocks/stubs/monkeypatched transport | Covered |
| R11 | Generator/validator must be adapter-based; validator mandatory at startup | `atomic_v2/step_01..03`, `atomic_v2/step_04..06`, `atomic_v2/step_07..09`, `atomic_v2/step_10..12`, `atomic_v2/step_17` | Verify generators/validators use adapter config primitives and one adapter config file; server start fails fast with logged validation errors; client init returns error and raises exception | Covered |

## Verification command templates (to be specialized per package/server)

### Shared quality gate

1. `code_mapper -r /home/vasilyvz/projects/ollama`
2. `black /home/vasilyvz/projects/ollama`
3. `flake8 /home/vasilyvz/projects/ollama`
4. `mypy /home/vasilyvz/projects/ollama`

### Server CLI

- `<server-cli> generate --output <path>`
- `<server-cli> validate --config <path>`
- `<server-cli> show-schema`
- `<server-cli> sample`

### Client CLI

- `<client-cli> generate --output <path>`
- `<client-cli> validate --config <path>`
- `<client-cli> show-schema`
- `<client-cli> test-connection --config <path>`

### Real E2E gate

- Bring up real services: proxy, adapter, redis, ollama, at least one extra tool server
- Execute integration tests and verification scripts without mocks
- Validate WS transport evidence in logs and artifacts

## Locked constraints (execution-ready baseline)

1. Package names locked in `atomic_v2/NAMING_FREEZE.md`:
   - `model_workspace_server`, `model_workspace_client`
   - `database_server`, `database_client`
2. WS contract locked: `ws-contract-v1` with explicit compatibility policy.
3. Publication strategy locked:
   - monorepo phase-1 with independent client distributions
   - `model-workspace-client`
   - `ollama-model-database-client`
