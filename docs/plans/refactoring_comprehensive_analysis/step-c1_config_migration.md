# STEP-C1 — Config migration: WorkstationConfig → provider_clients structure

**File:** `src/mwps/config.py`, `WorkstationConfig`
**Severity:** 🔴 High
**Depends on:** STEP-08 (provider clients ready to receive typed config)
**Blocks:** STEP-02 (config.py split happens after migration)

---

## Current state

`WorkstationConfig` (dataclass) has flat Model Workplace Server-specific fields:
- `mwps_url: str`
- `mwps_model: str`
- `mwps_embed_model: str`
- `request_timeout: int`

These are read by `provider_registry._build_mwps()` and
`docker_config_validation.py`.

## Target state

Replace flat fields with a typed `provider_clients` structure matching
`provider_client_config_standard.md`:

```python
@dataclass
class ProviderTransportConfig:
    base_url: str
    request_timeout_seconds: int = 120
    api_version: str = ""           # Google only

@dataclass
class ProviderAuthConfig:
    api_key: str = ""
    service_account_json: str = ""  # Google only

@dataclass
class ProviderFeaturesConfig:
    supports_stream: bool = True
    supports_tools: bool = True
    supports_embeddings: bool = False
    default_model: str = ""
    embed_model: str = ""
    # Provider-specific extras stored as dict:
    extra: dict = field(default_factory=dict)
    # e.g. anthropic_version, safety_settings

@dataclass
class ProviderLimitsConfig:
    max_tokens: int = 4096
    max_context_tokens: int = 131072

@dataclass
class ProviderSectionConfig:
    transport: ProviderTransportConfig
    auth: ProviderAuthConfig = field(default_factory=ProviderAuthConfig)
    features: ProviderFeaturesConfig = field(default_factory=ProviderFeaturesConfig)
    limits: ProviderLimitsConfig = field(default_factory=ProviderLimitsConfig)

@dataclass
class ProviderClientsConfig:
    default_provider: str
    providers: dict[str, ProviderSectionConfig]
```

`WorkstationConfig` gains:
```python
provider_clients: ProviderClientsConfig
```

And loses: `mwps_url`, `mwps_model`, `mwps_embed_model`,
`request_timeout`.

## Migration tasks

### C1a. Add ProviderSectionConfig dataclasses

New file `src/mwps/provider_config.py` with all dataclasses
above. Keeps `config.py` focused on loading logic.

### C1b. Update load_config()

Parse `provider_clients` section from YAML:
```python
def _parse_provider_section(raw: dict) -> ProviderSectionConfig:
    """Parse one provider section from raw config dict."""

def _parse_provider_clients(raw: dict) -> ProviderClientsConfig:
    """Parse entire provider_clients section. Validates V1–V4."""
```

Env-var interpolation for `${VAR}` in auth.api_key at parse time.

### C1c. Per-provider validation (V-PROV-1..6)

```python
def _validate_provider_section(
    name: str,
    section: ProviderSectionConfig,
    is_active: bool,
) -> list[str]:  # returns error messages
```

Validation runs for the **active** provider only (V5 in standard).
Other providers validated only if their section is present.

### C1d. Update provider_registry

`get_client(provider_name, config: ProviderClientsConfig)` reads
`config.providers[provider_name]` as `ProviderSectionConfig`.

### C1e. Update docker_config_validation

Replace `config.mwps_url`, `config.mwps_model` reads with
`config.provider_clients.providers["mwps"].transport.base_url`, etc.

### C1f. Config YAML migration

Document breaking change: old flat `mwps_url` key no longer works.
Provide migration example in `docs/` showing old → new structure.

## Acceptance criteria

- [ ] `WorkstationConfig` has no `mwps_url`, `mwps_model`, `mwps_embed_model`
- [ ] `provider_clients.providers.mwps` section parsed and typed
- [ ] Env-var `${VAR}` interpolated in `auth.api_key` at load time
- [ ] `validate_config()` catches missing active provider section (V4)
- [ ] `validate_config()` catches missing api_key for commercial providers (V6)
- [ ] `validate_config()` catches conflicting google auth (V-PROV-5)
- [ ] `docker_config_validation` updated to use new paths
- [ ] `provider_registry.get_client()` receives typed `ProviderSectionConfig`
- [ ] Migration guide written in `docs/provider_config_migration.md`
- [ ] `lint_code` + `type_check_code` pass
