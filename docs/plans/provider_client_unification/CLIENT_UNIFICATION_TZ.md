<!--
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
-->

# Provider Client Unification and MCP Control - Technical Assignment

## Purpose

Define a unified architecture where model workstation interacts with all providers through standardized clients, and model tool access to infrastructure (`redis`, `ollama`) is exposed through MCP Proxy via adapter-based servers with complete API coverage.

## Greenfield Priority

This project has not been used in production yet. Therefore, clean code and clean architecture have strict priority over backward compatibility.

Mandatory implications:

- Do not preserve legacy direct-access paths just for compatibility.
- Do not add compatibility shims that keep old and new runtime paths in parallel.
- Prefer clean replacement of outdated interfaces over staged long-term coexistence.
- Use migration-only compatibility toggles only if they are time-limited and explicitly documented for removal.

## Scope

This assignment covers:

1. Full MCP control for `redis` and `ollama` through proxy-registered adapter servers.
2. Unified channel acquisition for model communication through provider-specific clients.
3. Common workstation-level client API with internal transport/auth/format translation.
4. A standard for creating clients and a required abstract base class.
5. Configuration unification with standardized provider client sections.

Out of scope:

- Replacing MCP Proxy itself.
- Changing external provider APIs.
- Product UI/UX changes.

## Functional Requirements

### FR-1. Full MCP Proxy Control of Redis and Ollama

- `redis` and `ollama` capabilities must be available to the model only via MCP tool calls.
- Each backend must be represented by an adapter-based MCP server registered in proxy.
- Command surface must provide full API parity with backend capabilities used in production.
- No direct workstation calls to raw `redis` or raw `ollama` endpoints are allowed in runtime flow.

Minimum target server IDs:

- `database-server` (adapter facade for Redis domain operations)
- `ollama-server` (adapter facade for Ollama domain operations)

### FR-2. Provider Client Unification

- Communication with any model provider must go through a dedicated provider client.
- Ollama must be treated as a first-class provider, equivalent to commercial providers.
- Provider-specific transport/protocol/auth details must remain internal to each client.

### FR-3. Common Workstation Client API

- All provider clients must expose one uniform API in workstation terms.
- Message/tool/result format translation must occur inside client implementations.
- Workstation orchestration layer must be provider-agnostic.

### FR-4. Standard and Abstract Base Class

- A client development standard must define mandatory behavior, contracts, and errors.
- A shared abstract base class must define required methods/properties for all clients.
- All provider clients must implement this contract without partial stubs in production code.

### FR-5. Standardized Provider Client Config

- Config must contain a normalized provider-client section per provider.
- Each section must support transport/auth/TLS/protocol/provider-specific options.
- Validation must reject incomplete or conflicting provider client settings before runtime.

## Architecture Requirements

### AR-1. Access Path Policy

Allowed runtime paths:

- `workstation -> provider_client -> provider endpoint`
- `workstation -> ProxyClient -> call_server -> adapter server -> backend`

Forbidden runtime paths:

- `workstation -> raw redis`
- `workstation -> raw ollama`
- Any direct bypass around provider clients for model communication.

### AR-2. MCP Tool Surface Design

- `database-server` and `ollama-server` must publish complete command catalogs.
- Command metadata must include strict JSON Schema parameters.
- Tool-level auth/TLS constraints must align with proxy mTLS policy.

### AR-3. Uniform Error Model

Provider clients must normalize transport/provider errors into shared workstation error categories:

- `TransportError`
- `AuthError`
- `TimeoutError`
- `RateLimitError`
- `ProviderProtocolError`
- `ValidationError`

## Standardized Provider Client Interface

The abstract base class must define at least:

1. `validate_config()`
2. `healthcheck()`
3. `chat(request)`
4. `embed(request)` — see **Embed contract when unsupported** below.
5. `supports_tools()`
6. `normalize_response(raw_response)`
7. `map_error(exception)`

Additional requirements:

- Explicit capability flags (`supports_stream`, `supports_tools`, `supports_embeddings`).
- Deterministic timeout/retry behavior.
- Structured logging without secrets.

### Embed contract when capability unsupported

- The **method `embed(request)` is mandatory** for all provider clients: every client must implement it.
- If the provider does not support embeddings, the client must:
  - set **`supports_embeddings = False`** (or equivalent capability flag) so the workstation can avoid calling `embed` when not needed; and
  - implement **`embed(request)`** so that when called, it raises a **single, well-defined error** (e.g. `CapabilityNotSupportedError` or a documented subtype of `ValidationError`), without performing any network call.
- The workstation must check `supports_embeddings` before calling `embed`; if it calls `embed` on a client that reported `supports_embeddings=False`, the client’s raising the defined error is acceptable and considered correct behavior.
- Summary: **no optional `embed`** — the method is always present; unsupported embeddings are expressed by the flag plus a defined error on call.
- **Not allowed:** the variant «only a capability flag without implementing the `embed` method» — the method must always be implemented; the «flag only, no method» option is explicitly disallowed.

## Configuration Standard

Target normalized structure:

- `provider_clients.default_provider`
- `provider_clients.providers.<provider_name>.transport`
- `provider_clients.providers.<provider_name>.auth`
- `provider_clients.providers.<provider_name>.tls`
- `provider_clients.providers.<provider_name>.features`
- `provider_clients.providers.<provider_name>.limits`

Example provider names:

- `ollama`
- `openai`
- `anthropic`
- `google`
- `xai`
- `deepseek`

Validation rules:

- Active provider section must exist and pass schema validation.
- Auth requirements must match selected protocol.
- TLS requirements must match selected endpoint/protocol.

## Implementation Deliverables

1. Client standard document (normative rules).
2. Abstract base class for provider clients.
3. Concrete provider clients migrated to the shared contract.
4. Workstation orchestration refactor to provider-client-only path.
5. MCP adapter servers exposing full `redis` and `ollama` tool surfaces.
6. Config schema/generator/validator updates for standardized provider client sections.
7. Integration tests for:
   - no-direct-access policy
   - provider parity through common API
   - proxy registration and command availability

## Acceptance Criteria

1. Workstation runtime has no direct `redis`/`ollama` access path.
2. Model interaction for all providers is performed via provider clients only.
3. `database-server` and `ollama-server` are proxy-registered and command-discoverable.
4. Published command sets cover agreed backend API surface.
5. Provider client config validation blocks invalid startup.
6. Integration and E2E tests confirm client-only and proxy-mediated architecture.

## Migration Notes

- Existing direct-access configuration fields should be removed from runtime usage and migrated to provider-client sections.
- Backward compatibility is not a default requirement for this project stage.
- If temporary compatibility is introduced for migration, it must have strict removal criteria and deadline.
- Final target state removes direct transport fields from workstation runtime config.
