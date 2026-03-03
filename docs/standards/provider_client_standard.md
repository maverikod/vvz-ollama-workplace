<!--
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
-->

# Provider Client Standard (Normative)

This document is the **single source of truth** for the abstract base class and all concrete provider clients. Implementations (abstract base class in step 04 and concrete clients) MUST follow this standard.

References: [CLIENT_UNIFICATION_TZ.md](../plans/provider_client_unification/CLIENT_UNIFICATION_TZ.md), [SCOPE_FREEZE.md](../plans/provider_client_unification/atomic/SCOPE_FREEZE.md).

---

## 1. Purpose and scope

- **Provider client**: a component that communicates with a single model provider (e.g. Ollama, OpenAI) on behalf of the workstation. Transport, protocol, and auth details are internal to the client.
- **Workstation**: uses only the uniform API defined below; it is provider-agnostic.
- All provider clients MUST implement the mandatory behaviour, required methods, capability flags, and error mapping defined in this document. No partial stubs in production code.

---

## 2. Mandatory behaviour and contracts

### 2.1 Lifecycle and configuration

- Configuration MUST be validated before the client is used for chat, embed, or healthcheck. Validation MUST be performed via `validate_config()` (see § 3).
- The client MUST NOT perform network calls in the constructor for optional or lazy setup unless explicitly documented; required connectivity checks belong in `healthcheck()`.

### 2.2 Workstation-facing API

- The workstation MUST be able to: validate config, run healthcheck, send chat requests, optionally send embed requests (when capability is supported), and obtain normalized responses and mapped errors.
- All provider-specific details (URLs, headers, request/response shapes) MUST remain inside the client. The workstation sees only the standard request/response and error types defined here.

### 2.3 Determinism and safety

- Timeout and retry behaviour MUST be deterministic and configurable (see § 7). No unbounded waits in production code.
- Logging MUST NOT include secrets (API keys, tokens, passwords). Logs MAY include non-sensitive identifiers (e.g. provider name, request id) for diagnostics.

---

## 3. Required methods

Every provider client MUST implement the following methods. Signatures and semantics are normative; the abstract base class (step 04) MUST declare them accordingly.

| Method | Purpose | Contract |
|--------|---------|----------|
| **validate_config()** | Validate client configuration before use. | Raises nothing if config is valid. Raises a defined error (e.g. `ValidationError` or a subtype from § 6) if config is invalid, incomplete, or conflicting. MUST NOT perform network I/O. |
| **healthcheck()** | Check that the provider endpoint is reachable and acceptable. | Returns a result indicating success or failure (e.g. boolean or a small result object). MAY perform a lightweight network call. MUST map provider/transport failures to the error categories in § 6 (e.g. via `map_error`). |
| **chat(request)** | Send a chat (completion) request to the provider. | Accepts a workstation-standard chat request. Returns a normalized response (see `normalize_response`). MUST respect timeout/retry rules. MUST use `map_error` for any exception that is not already in the standard error set. |
| **embed(request)** | Request embeddings for the given input. | **Mandatory for all clients** (see § 4). If the provider does not support embeddings, the client sets `supports_embeddings = False` and implements `embed(request)` to raise the defined error (e.g. `CapabilityNotSupportedError`) without performing a network call. If the provider supports embeddings, performs the request and returns normalized embedding response. |
| **supports_tools()** | Report whether the client supports tool/function calling. | Returns a boolean. MUST be constant for the lifetime of the client (derived from config/capability). No side effects. |
| **normalize_response(raw_response)** | Convert provider-specific raw response to workstation-standard shape. | Accepts the raw response from the provider (e.g. HTTP response body or parsed object). Returns a single, well-defined workstation format (e.g. chat response with message, finish reason, usage). MUST NOT raise for well-formed raw responses; invalid or unexpected shapes MAY raise `ProviderProtocolError` or `ValidationError`. |
| **map_error(exception)** | Map a provider or transport exception to a standard error category. | Accepts an exception (e.g. from HTTP client, SDK, or provider API). Returns or raises exactly one of: `TransportError`, `AuthError`, `TimeoutError`, `RateLimitError`, `ProviderProtocolError`, `ValidationError` (and `CapabilityNotSupportedError` where applicable). Used internally by `chat`, `embed`, `healthcheck` so the workstation sees only standard errors. |

---

## 4. Embed contract when capability unsupported

- The **method `embed(request)` is mandatory** for every provider client: every client MUST implement it.
- If the provider **does not support embeddings**:
  - The client MUST set **`supports_embeddings = False`** (or equivalent capability flag) so the workstation can avoid calling `embed` when not needed.
  - The client MUST implement **`embed(request)`** so that when called, it raises a **single, well-defined error** (e.g. `CapabilityNotSupportedError`, or a documented subtype of `ValidationError` from the shared error module), **without performing any network call**.
- The workstation SHOULD check `supports_embeddings` before calling `embed`. If the workstation calls `embed` on a client that reported `supports_embeddings = False`, the client’s raising the defined error is acceptable and considered correct behaviour.
- **Not allowed:** implementing only a capability flag without implementing the `embed` method. The method MUST always be present; unsupported embeddings are expressed by the flag plus the defined error on call.

---

## 5. Capability flags

Every provider client MUST expose the following capability flags (as attributes or properties). They MUST be constant for the lifetime of the client (typically derived from config or provider capability).

| Flag | Type | Meaning |
|------|------|---------|
| **supports_stream** | bool | Whether the client can return streaming chat responses. If `False`, the client returns only non-streaming responses. |
| **supports_tools** | bool | Whether the client supports tool/function calling. Must match the return value of `supports_tools()`. |
| **supports_embeddings** | bool | Whether the client supports embedding requests. If `False`, `embed(request)` MUST be implemented and MUST raise the defined error (e.g. `CapabilityNotSupportedError`) when called, without performing a network call. |

The workstation uses these flags to decide whether to call streaming APIs, pass tool definitions, or call `embed`. Clients MUST not advertise a capability they do not fully support.

---

## 6. Error categories

Provider clients MUST normalize all failures into the following categories. The shared error module (step 03) MUST define these types; clients use them in `map_error`, `validate_config`, and internally in `chat` / `embed` / `healthcheck`.

| Error | When to use |
|-------|-------------|
| **TransportError** | Network-level failures: connection refused, DNS failure, connection reset, TLS handshake failure, etc. |
| **AuthError** | Authentication or authorization failures: invalid API key, expired token, 401/403 from provider. |
| **TimeoutError** | Request or operation exceeded the configured timeout. |
| **RateLimitError** | Provider returned rate limit (e.g. 429) or quota exceeded. |
| **ProviderProtocolError** | Provider returned an unexpected or malformed response; protocol violation; unsupported response shape. |
| **ValidationError** | Invalid request parameters, invalid config, or client-side validation failure. |
| **CapabilityNotSupportedError** | The requested capability (e.g. embeddings) is not supported by this client/provider. MUST be used by `embed()` when `supports_embeddings = False` (see § 4). May be a subtype of `ValidationError` or a standalone class as defined in step 03. |

All exceptions that escape from client methods (except internal programming errors) MUST be one of the above. The workstation MUST NOT be required to handle provider-specific exception types.

---

## 7. Timeout and retry rules

- **Timeout**: Every client MUST support a configurable timeout for chat and embed requests (and optionally healthcheck). The timeout MUST be applied consistently; no unbounded waits. Default and max values MAY be defined in the config standard (step 02).
- **Retry**: Retry behaviour (if any) MUST be deterministic and configurable. Recommended: retry only on transient failures (e.g. `TransportError`, `TimeoutError`, or specific `RateLimitError` with Retry-After). MUST NOT retry on `AuthError` or `ValidationError`. Retry count and backoff MUST be bounded and documented.
- **Logging**: On retry, log at most one summary per request (e.g. "retry attempt N of M") without secrets. Do not log request/response bodies that may contain tokens or PII.

---

## 8. Logging rules (no secrets)

- MUST NOT log: API keys, bearer tokens, passwords, or any credential.
- MAY log: provider name, request/response size, status codes, error category, retry attempt, timeout values, non-sensitive config keys (e.g. `base_url` host part without query or path if sensitive).
- Structured logging is preferred (e.g. structured fields for error category, provider, operation). Log level and importance (0–10) should follow project logging standards.

---

## 9. Summary checklist for implementations

- [ ] Implement `validate_config()`, `healthcheck()`, `chat(request)`, `embed(request)`, `supports_tools()`, `normalize_response(raw_response)`, `map_error(exception)`.
- [ ] Expose capability flags: `supports_stream`, `supports_tools`, `supports_embeddings`.
- [ ] When embeddings are unsupported: `supports_embeddings = False` and `embed()` raises the defined error without network call.
- [ ] Map all failures to the standard error categories (§ 6).
- [ ] Apply configurable timeout and bounded retry; no secrets in logs.

Step 04 (abstract base class) can be implemented by following this document alone.
