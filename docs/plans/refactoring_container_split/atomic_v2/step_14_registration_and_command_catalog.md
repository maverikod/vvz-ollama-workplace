# Step 14: Registration and Command Catalog

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

## Target file
- `src/ollama_workstation/registration.py`

## Dependencies
- `NAMING_FREEZE.md` (mandatory naming/source of truth)
- `../QUALITY_GATE.md`

## Detailed scope
- Correct registration through `mcp-proxy-adapter`.
- Ensure command metadata detail level is not lower than `man`.
- Ensure strict command schemas are discoverable via help/discovery.
- Apply fixed registration target from `NAMING_FREEZE.md`:
  - proxy base URL from config (`<proxy_base_url>`)
  - current stage value may be `https://172.28.0.2:3004`
  - `registration.protocol = mtls`
  - URLs: `/register`, `/unregister`, `/proxy/heartbeat`
  - cert paths from `mtls_certificates` (`ca`, `client`, `server` trees)

## Success metric
- Real discovery/help returns full command set with detailed metadata and valid schemas.
- Registration succeeds against configured proxy base URL with mTLS enabled.

## Blocking protocol (mandatory)
- If any requirement is unclear, contradictory, or underspecified: **STOP** implementation.
- Ask a clarifying question and proceed only after explicit clarification.
