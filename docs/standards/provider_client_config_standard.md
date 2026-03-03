<!--
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
-->

# Provider Client Configuration Standard

Normative document for the provider client configuration structure and validation rules. Steps 05 (schema), 06 (validator), and 07 (generator) must be implemented by following this document alone.

References: [CLIENT_UNIFICATION_TZ.md](../plans/provider_client_unification/CLIENT_UNIFICATION_TZ.md) (Configuration Standard), [SCOPE_FREEZE.md](../plans/provider_client_unification/atomic/SCOPE_FREEZE.md).

---

## 1. Normalized structure

All provider client configuration lives under a single top-level key: **`provider_clients`**.

### 1.1 Top-level keys

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `default_provider` | string | yes | Name of the provider to use when no provider is specified. Must reference an existing key under `provider_clients.providers`. |
| `providers` | object | yes | Map of provider names to provider sections. At least one provider must be defined; the provider named in `default_provider` must be present. |

### 1.2 Per-provider section: `provider_clients.providers.<provider_name>`

Each entry under `providers` is keyed by **provider name** (see §2). The value is an object with the following normalized keys:

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `transport` | object | yes | Transport/protocol settings (e.g. base URL, protocol type, timeouts). Must be consistent with auth and TLS. |
| `auth` | object | conditional | Authentication settings. Required when the selected protocol/endpoint requires auth; optional otherwise. Must match protocol (e.g. API key for REST, mTLS client cert path for TLS). |
| `tls` | object | conditional | TLS settings (e.g. verify, client cert, CA). Required when the endpoint uses HTTPS or secure protocol; optional for plain HTTP. Must match endpoint and protocol. |
| `features` | object | optional | Provider-specific feature flags or options (e.g. supports_stream, supports_tools, model-specific caps). |
| `limits` | object | optional | Limits (e.g. max_tokens, timeout_seconds, rate limits). |

**Normative:** The structure is **flat per provider**: one section per provider name; no nested "provider type" under a single name. All provider-specific configuration for a given provider is under `provider_clients.providers.<provider_name>` with the five sub-keys above (transport, auth, tls, features, limits).

---

## 2. Example provider names

The following provider names are **canonical** for the config standard and schema. They use lowercase, hyphen-free identifiers.

| Provider name | Notes |
|---------------|--------|
| `ollama` | First-class provider; mandatory to support in phase 1. |
| `openai` | Example external provider; supported by config/schema; concrete client optional in phase 1. |
| `anthropic` | Example external provider. |
| `google` | Example external provider. |
| `xai` | Example external provider. |
| `deepseek` | Example external provider. |

Implementations (schema, validator, generator) must accept at least these names. Additional provider names may be allowed if they follow the same naming rule (lowercase, hyphen-free). The **active** provider is the one named in `default_provider`; its section must exist and pass validation.

---

## 3. Validation rules

Validation must run **before runtime**. Invalid or conflicting configuration must **block startup** (fail fast).

### 3.1 Presence and schema

- **V1** The key `provider_clients` must exist and be an object.
- **V2** The key `provider_clients.default_provider` must exist and be a non-empty string.
- **V3** The key `provider_clients.providers` must exist and be an object with at least one entry.
- **V4** The provider named in `provider_clients.default_provider` must exist as a key under `provider_clients.providers`.
- **V5** The active provider section (the one referenced by `default_provider`) must pass the full provider-section schema (transport required; auth/tls/features/limits as per schema and protocol).

### 3.2 Auth and protocol

- **V6** If the selected transport/protocol requires authentication (e.g. API key, bearer token), the `auth` section must be present and contain the required fields (e.g. `api_key`, `bearer_token`). Validation must reject missing or empty required auth when the protocol requires it.
- **V7** If the selected transport does not use auth, the `auth` section may be absent or empty; no auth fields are required.

### 3.3 TLS and endpoint

- **V8** If the endpoint URL or protocol implies TLS (e.g. `https://`, secure channel), the `tls` section must be present and consistent (e.g. `verify` flag, optional client cert paths). Validation must reject insecure or inconsistent TLS when the endpoint is secure.
- **V9** If the endpoint is plain HTTP and does not use TLS, the `tls` section may be absent or minimal; no TLS fields are required.

### 3.4 Conflicts and completeness

- **V10** Validation must reject **incomplete** provider client settings: e.g. active provider section missing, required `transport` missing, or required auth/TLS missing for the chosen protocol/endpoint.
- **V11** Validation must reject **conflicting** settings: e.g. protocol says "HTTPS" but TLS is disabled or missing; auth type does not match protocol; duplicate or mutually exclusive options set together.

**Normative:** No runtime use of provider client config is allowed until validation passes. The validator (step 06) implements these rules; the schema (step 05) defines the structure so that the validator can enforce V1–V11.

---

## 4. Relation to schema, validator, and generator

- **Schema (step 05):** Must define the structure of `provider_clients` and of each `provider_clients.providers.<name>` entry (transport, auth, tls, features, limits) so that valid configs are representable and invalid ones can be detected.
- **Validator (step 06):** Must enforce V1–V11 and run before runtime; must reject incomplete or conflicting provider client settings.
- **Generator (step 07):** Must produce only valid `provider_clients` sections that pass the validator (and thus satisfy this standard).

This document is the single normative source for the config structure and validation rules for provider clients.
