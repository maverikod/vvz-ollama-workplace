# Step 01: Config schema and command policy

**Author:** Vasiliy Zdanovskiy  
**Email:** vasilyvz@gmail.com  

**Scope:** Introduce config schema for allowed/forbidden commands and policy. One step = one file (this doc); implementation may add one or more code files.

## Goal

- Add to workstation/adapter config:
  - `allowed_commands` — list of command identifiers (optional).
  - `forbidden_commands` — list of command identifiers (takes precedence).
  - `commands_policy` — `allow_by_default` or `deny_by_default`.
- **allow_by_default:** Expose all discovered commands except those in `forbidden_commands`. If `allowed_commands` is non-empty, treat it as an additional filter: only commands that are in both the discovered set and `allowed_commands` pass (minus forbidden). If `allowed_commands` is empty, expose all discovered minus forbidden.
- **deny_by_default:** Expose only commands in `allowed_commands` minus `forbidden_commands`.
- Policy is always from config; session lists only refine the set (see step 05, 06, 13).

## Objects

- **CommandsPolicyConfig** (or equivalent): holds `allowed_commands`, `forbidden_commands`, `commands_policy`. Loaded from YAML/JSON config.

## Inputs / outputs

- **Input:** Config file (e.g. `ollama_workstation` section).
- **Output:** In-memory structure usable by EffectiveToolListBuilder (step 06): apply policy + lists to a candidate set of commands.

## Acceptance criteria

- Config schema includes the three fields; validation rejects invalid `commands_policy` value.
- For a given candidate set: under `deny_by_default`, only candidates in `allowed_commands` and not in `forbidden_commands` pass; under `allow_by_default`, all candidates except those in `forbidden_commands` pass.
- Documented in project config example and standards.

## References

- Main plan: [§1.4 Config: allowed / forbidden commands and policy](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#14-config-allowed--forbidden-commands-and-policy) (allowed_commands, forbidden_commands, commands_policy; **command_discovery_interval_sec** is added in step_03), [§1 Object model](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#object-model-by-object-scheme) (CommandsPolicyConfig).
- Objects and diagrams: [00_objects_and_diagrams.md](00_objects_and_diagrams.md).
- Next: [step_02_safe_name_and_registry.md](step_02_safe_name_and_registry.md). Consumed by step 06.

## Success metrics

- **Step-specific:** Config schema has `allowed_commands`, `forbidden_commands`, `commands_policy`; validation rejects invalid `commands_policy`; for a candidate set, deny_by_default ⇒ only allowed minus forbidden; allow_by_default ⇒ all minus forbidden.
- **Standard verification:** No incomplete code, TODO, ellipsis, or syntax issues; no `pass` outside exceptions; no `NotImplemented` outside abstract methods; no deviations from [RULES](../../RULES.md) or plan. After code: `code_mapper -r src` (fix errors); `mypy src`, `flake8 src tests`, `black src tests` (fix all).

## Config generator and validator (adapter-first)

- **Generator:** The project uses the adapter’s `SimpleConfigGenerator` (from mcp_proxy_adapter) to produce the base config; then applies project overrides (see `docker/generate_config.py`, `container/generate_config.py`). When adding commands policy config, the **generator** must be updated to include the new fields in the `ollama_workstation` overlay (e.g. `allowed_commands`, `forbidden_commands`, `commands_policy` with defaults) so that generated `adapter_config.json` is valid and complete.
- **Validator:** Validation is two-stage: (1) adapter’s `SimpleConfig.validate()`, (2) project’s `validate_project_config(app_config)` (in `src/ollama_workstation/docker_config_validation.py`). When adding commands policy, the **project-specific validator** must be extended to validate the new fields (e.g. `commands_policy` in `["allow_by_default", "deny_by_default"]`; `allowed_commands` and `forbidden_commands` as lists of strings if present). See main plan [§6.4 Config generator and validator](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#64-config-generator-and-validator-project-vs-adapter).

## Comparative analysis vs existing code

| Aspect | Existing | To change | To add |
|--------|----------|-----------|--------|
| Config | `config.py`: `WorkstationConfig` (mcp_proxy_url, ollama_*, max_tool_rounds) | Extend loader to read `ollama_workstation` section for commands policy | `CommandsPolicyConfig` (or fields in config model): allowed_commands, forbidden_commands, commands_policy |
| Example config | `config/ollama_workstation.example.yaml` has no commands section | — | Example snippet for allowed_commands, forbidden_commands, commands_policy |
| Validation | Required fields validated in `__post_init__`; `validate_project_config` checks mTLS and ollama_models | — | Validate commands_policy enum; optional validation for list types in `validate_project_config` |
| **Config generator** | `docker/generate_config.py` uses adapter generator then sets `ollama_workstation` (mcp_proxy_url, ollama_*, max_tool_rounds) | — | Add to generator overlay: `allowed_commands`, `forbidden_commands`, `commands_policy` (with defaults, e.g. allow_by_default, empty lists) |

## Dependencies

- None (foundational). Step 06 consumes this.

## Deliverable

- Config model/schema and validation; example config snippet; **update config generator** (docker and/or container) to include new `ollama_workstation` fields; **update project-specific validator** (`validate_project_config`) for the new fields; optional unit tests.
