# Step 17: Real Integration (No Mocks)

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

## Target file
- `tests/integration/test_proxy_and_servers.py`

## Dependencies
- `NAMING_FREEZE.md` (mandatory naming/source of truth)
- `../QUALITY_GATE.md`

## Detailed scope
- Integration only on real services: proxy, workstation, db, ollama, real tool server.
- Validate both pair contracts (model-workspace + database).
- No mocked transport/stubs.
- Use real configured proxy endpoint (`<proxy_base_url>`) with `mTLS` registration and certs from `mtls_certificates`.
- Endpoint must be provided by environment/config (for example `MCP_PROXY_URL`);
  do not hardcode container IP addresses.

## Success metric
- Test suite passes only with real service topology and fails when required service is absent.
- Registration test fails when mTLS cert paths are invalid and passes with valid cert set.

## Blocking protocol (mandatory)
- If any requirement is unclear, contradictory, or underspecified: **STOP** implementation.
- Ask a clarifying question and proceed only after explicit clarification.
