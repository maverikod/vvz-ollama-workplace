<!--
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
-->

# Step 01: Client Standard Document

## Target file

- `docs/standards/provider_client_standard.md` (canonical path in [SCOPE_FREEZE.md](SCOPE_FREEZE.md))

## Dependencies

- [SCOPE_FREEZE.md](SCOPE_FREEZE.md)
- [../QUALITY_GATE.md](../QUALITY_GATE.md)
- [../CLIENT_UNIFICATION_TZ.md](../CLIENT_UNIFICATION_TZ.md) (Standardized Provider Client Interface, Embed contract)

## Detailed scope

- Write normative document defining:
  - Mandatory behaviour and contracts for provider clients.
  - Required methods: `validate_config()`, `healthcheck()`, `chat(request)`, `embed(request)`, `supports_tools()`, `normalize_response(raw_response)`, `map_error(exception)`.
  - Embed contract when unsupported: method mandatory; `supports_embeddings=False`; `embed()` raises defined error (e.g. CapabilityNotSupportedError).
  - Capability flags: `supports_stream`, `supports_tools`, `supports_embeddings`.
  - Error categories (TransportError, AuthError, TimeoutError, RateLimitError, ProviderProtocolError, ValidationError).
  - Timeout/retry and logging rules (no secrets).
- Document is the single source of truth for the abstract base class and concrete clients.

## Success metric

- Document exists at the target path.
- It defines all required methods, capability flags, error categories, and the embed contract.
- Step 04 (abstract base class) can be implemented by following this document alone.

## Blocking protocol (mandatory)

- If any requirement is unclear, contradictory, or underspecified: **STOP** implementation.
- Ask a clarifying question and proceed only after explicit clarification.
