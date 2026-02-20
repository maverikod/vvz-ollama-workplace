# Step 03: Command discovery from proxy

**Author:** Vasiliy Zdanovskiy  
**Email:** vasilyvz@gmail.com  

**Scope:** Obtain the list of servers and their command schemas from the proxy; build a flat list of commands (CommandId + CommandSchema). One step = one file (this doc).

## Goal

- Call proxy **list_servers** (existing) to get server_id, server_url, and if available command list per server.
- For each server, obtain command schemas (e.g. via proxy **help** or a schema endpoint); get command name, description, parameters (JSON Schema).
- Build **command_id** = `CommandName.ServerId` (e.g. `echo.ollama-adapter`, `chunk.svo-chunker`).
- Produce a single flat list of (CommandId, CommandSchema) for downstream filtering and tool-list build.

## Objects

- **CommandId:** Value object or canonical string: command_name + "." + server_id.
- **CommandSchema:** name, description, parameters (JSON Schema). From proxy.
- **CommandDiscovery:** Fetches list_servers; for each server fetches schemas; builds and returns/caches list of (CommandId, CommandSchema). **Update strategy:** on startup (fetch from proxy) and **periodically** with **configurable interval** (`command_discovery_interval_sec`). When a server is unreachable (e.g. health or schema fetch fails), **mark that server's commands as unavailable** (do not remove from the list); see main plan §1.2.

## Inputs / outputs

- **Input:** Proxy client (list_servers, help or schema per server); optional refresh trigger.
- **Output:** List of (command_id, CommandSchema). Consumed by EffectiveToolListBuilder (step 06) after policy filter.

## Acceptance criteria

- All discovered commands have a unique command_id. Schema includes at least name and description; parameters can be empty or full JSON Schema.
- If proxy or a server is unavailable: keep cached list; **mark commands of the unavailable server as unavailable** (flag or separate "available" set); log. Do not remove commands from the discovered list.
- Update strategy: **on startup** + **periodic** with config parameter `command_discovery_interval_sec` (see main plan §1.2 and §1.4).

## References

- Main plan: [§1.2 Update strategy (dynamic)](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#12-update-strategy-dynamic), [§1.3 Data flow](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#13-data-flow), [§1.4 Config](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#14-config-allowed--forbidden-commands-and-policy), [§1 Object model](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#object-model-by-object-scheme) (CommandId, CommandSchema, CommandDiscovery).
- Objects and diagrams: [00_objects_and_diagrams.md](00_objects_and_diagrams.md).
- Prev: [step_02_safe_name_and_registry.md](step_02_safe_name_and_registry.md). Next: [step_04_command_aliases.md](step_04_command_aliases.md). Consumed by step 06 with step 01.

## Success metrics

- **Step-specific:** Every discovered command has unique command_id; schema has at least name and description; parameters optional (JSON Schema or empty); when server unavailable, its commands marked unavailable and logged; update strategy = startup + periodic with `command_discovery_interval_sec`.
- **Standard verification:** No incomplete code, TODO, ellipsis, or syntax issues; no `pass` outside exceptions; no `NotImplemented` outside abstract methods; no deviations from [RULES](../../RULES.md) or plan. After code: `code_mapper -r src`; `mypy src`, `flake8 src tests`, `black src tests` (fix all).

## Comparative analysis vs existing code

| Aspect | Existing | To change | To add |
|--------|----------|-----------|--------|
| Proxy | `proxy_client.py`: list_servers(), help(server_id, command) | None | CommandDiscovery: call list_servers, then per-server help/schema; build flat list |
| Tools | `tools.py`: get_ollama_tools() returns fixed list | — | CommandId (value), CommandSchema (name, description, parameters); discovery output feeds EffectiveToolListBuilder (step 06) |
| Chat | `chat_flow.py` uses get_ollama_tools() | — | Chat flow will later use discovered commands + registry (steps 06, 02) |

## Dependencies

- Proxy client (existing). Step 01 (policy) and step 06 consume discovery output.

## Deliverable

- CommandId and CommandSchema types; CommandDiscovery class and integration with proxy (startup + periodic with `command_discovery_interval_sec`; mark unavailable when server down). Add **command_discovery_interval_sec** to config (generator overlay and `validate_project_config` per main plan §6.4). Unit tests with mocked proxy.
