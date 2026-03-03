<!--
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
-->

# Step 10: Workstation Orchestration Refactor

## Target file

- `src/ollama_workstation/chat_flow.py` and any other modules that perform model communication or direct redis/ollama access. Exact list: see [SCOPE_FREEZE.md](SCOPE_FREEZE.md) § Step_10: modules touched.

## Dependencies

- [SCOPE_FREEZE.md](SCOPE_FREEZE.md)
- [step_08_ollama_provider_client.md](step_08_ollama_provider_client.md)
- [step_09_provider_client_registry.md](step_09_provider_client_registry.md)
- [step_06_provider_client_config_validator.md](step_06_provider_client_config_validator.md)
- [../QUALITY_GATE.md](../QUALITY_GATE.md)
- [../CLIENT_UNIFICATION_TZ.md](../CLIENT_UNIFICATION_TZ.md) (FR-1, AR-1, Migration Notes)

## Detailed scope

- Refactor workstation so that **all** model communication goes through provider clients (obtained via registry).
- Remove any direct calls to raw redis or raw ollama endpoints from the runtime flow; redis/ollama access for the model only via ProxyClient → call_server → adapter (MCP).
- Remove direct transport fields from workstation runtime config (migrate to normalized provider-client sections), per TZ Migration Notes.
- Provider client config validation runs at startup; invalid config blocks startup.
- Orchestration layer is provider-agnostic (uses common API only).

## Success metric

- No code path in workstation runtime: workstation → raw redis or workstation → raw ollama for model communication.
- Model chat/embed flows use only provider clients; tool calls use only ProxyClient → call_server.
- Startup fails with clear error when provider client config is invalid.

## Blocking protocol (mandatory)

- If any requirement is unclear, contradictory, or underspecified: **STOP** implementation.
- Ask a clarifying question and proceed only after explicit clarification.
