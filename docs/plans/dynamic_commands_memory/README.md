# Dynamic commands and memory — step-by-step plan

**Author:** Vasiliy Zdanovskiy  
**Email:** vasilyvz@gmail.com  

This subdirectory contains the **step-by-step implementation plan** for the [Dynamic commands and Redis memory](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md) feature. **One step = one file.** Each step file describes scope, objects, inputs/outputs, and acceptance criteria.

## Index

| Step | File | Summary |
|------|------|--------|
| — | [00_objects_and_diagrams.md](00_objects_and_diagrams.md) | Object scheme and Mermaid interaction diagrams |
| — | [SCHEMA_REFERENCE.md](SCHEMA_REFERENCE.md) | Pointer to §3.5 Schema and structure of data stores (in main plan) |
| 01 | [step_01_config_and_policy.md](step_01_config_and_policy.md) | Config schema: allowed/forbidden commands, policy |
| 02 | [step_02_safe_name_and_registry.md](step_02_safe_name_and_registry.md) | Safe name translation and tool-call registry |
| 03 | [step_03_command_discovery.md](step_03_command_discovery.md) | Command discovery from proxy (list_servers, schemas) |
| 04 | [step_04_command_aliases.md](step_04_command_aliases.md) | Command alias registry per model |
| 05 | [step_05_session_store.md](step_05_session_store.md) | Session entity and SessionStore |
| 06 | [step_06_effective_tool_list.md](step_06_effective_tool_list.md) | Effective tool list builder (config + session merge) |
| 07 | [step_07_context_representation_base.md](step_07_context_representation_base.md) | Context representation base and registry |
| 08 | [step_08_ollama_representation.md](step_08_ollama_representation.md) | Ollama representation implementation |
| 09 | [step_09_redis_message_writer.md](step_09_redis_message_writer.md) | Redis message stream writer |
| 10 | [step_10_context_builder.md](step_10_context_builder.md) | Context builder (trimming, slots) |
| 11 | [step_11_documentation_source.md](step_11_documentation_source.md) | Documentation source interface and slot builder |
| 12 | [step_12_call_stack_and_depth.md](step_12_call_stack_and_depth.md) | Call stack and model-call depth guard |
| 13 | [step_13_session_commands.md](step_13_session_commands.md) | Session-init and add/remove command to session |
| — | [14_ambiguities_and_open_points.md](14_ambiguities_and_open_points.md) | Ambiguities, open points, and resolutions (reference) |

## How to use

- Read the main plan first: [../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md).
- Use [00_objects_and_diagrams.md](00_objects_and_diagrams.md) for the object list and interaction diagrams.
- Check [14_ambiguities_and_open_points.md](14_ambiguities_and_open_points.md) for resolved ambiguities and TBD items before implementation.
- Implement in order step_01 … step_13; each step produces one or more modules/files. Dependencies between steps are stated in each file.

## Chat flow integration checklist

After implementing the relevant steps, ensure **chat flow** (e.g. `chat_flow.py` or the component that handles ollama_chat) is wired as follows:

- **session_id** — required on every chat/context request (obtained from SessionInitCommand; step 13).
- **Tool list** — build via EffectiveToolListBuilder(session, config, discovery, alias registry, …); resolve tool calls by display_name → (command_name, server_id) using ToolCallRegistry (steps 06, 02, 04).
- **Message stream** — after each user/model/tool message, call MessageStreamWriter.write(record) with uuid, created_at, source, body, session_id (step 09; field names aligned with chunk_metadata_adapter). Schema of the message store: main plan [§3.5.1](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#351-redis-message-store-redismessagerecord).
- **Context** — build via ContextBuilder(session_id, current_message, config); uses SessionStore, RepresentationRegistry, message source, RelevanceSlotBuilder (steps 10, 05, 07, 09). When using semantic search: obtain **query embedding** via **embed client** (e.g. embed_client), then k-NN per main plan §4.2b. When using semantic/BM25 search: results keyed by chunk_id; resolution and filter (is_deleted) per §4.2b, §3.5.4.
- **Tool → model** — before invoking the model from a tool (e.g. ollama_chat), call ModelCallDepthGuard; use CallStack and allow-list (step 12).

No separate "integration step" is defined; each step deliverable includes wiring where applicable. **Schema reference:** All store schemas (Redis message, Session, vector table, external Database) are in main plan [§3.5 Schema and structure of data stores](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#35-schema-and-structure-of-data-stores-reference).

## Code quality and step success metrics

Requirements are synced with **flake8** (max-line-length = 88), **mypy** (see pyproject.toml), and **black** (line-length = 88). See main plan [§6 Code quality and step success metrics](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#6-code-quality-and-step-success-metrics).

Each step file contains:

1. **References** — links to main plan, [00_objects_and_diagrams.md](00_objects_and_diagrams.md), and dependent steps so the step is self-contained.
2. **Success metrics** — step-specific parameters/checks and the standard verification checklist:
   - No incomplete code, TODO/FIXME in production, ellipsis or syntax violations; no `pass` outside exceptions; no `NotImplemented` outside abstract methods; no deviations from project/plan rules.
   - After code: run `code_mapper -r src` and fix errors; run `mypy src`, `flake8 src tests`, `black src tests` and fix all issues.
3. **Comparative analysis** — what to change and what to add vs existing code (per step).
