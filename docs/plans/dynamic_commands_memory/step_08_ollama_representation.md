# Step 08: Ollama representation implementation

**Author:** Vasiliy Zdanovskiy  
**Email:** vasilyvz@gmail.com  

**Scope:** Implement ContextRepresentation for the OLLAMA API: serialize tools and messages in the format expected by OLLAMA chat. One step = one file (this doc).

## Goal

- **OllamaRepresentation** implements ContextRepresentation for OLLAMA: tool format (type "function", function with name, description, parameters as JSON Schema), and message format (role, content or parts as used by OLLAMA).
- Register Ollama models in RepresentationRegistry so that sessions using these models get OllamaRepresentation. **At startup:** populate the registry from config (e.g. `ollama_models` or model list that uses Ollama representation); each such model_id → OllamaRepresentation instance, so that ContextBuilder and chat flow can call get_representation(session.model) and get the correct serializer.

## Objects

- **OllamaRepresentation:** Concrete class; serialize_tools(tool_list) → OLLAMA tools; serialize_messages(messages) → OLLAMA messages; format_tool_result(raw_result) → JSON string or str (tool message content).

## Inputs / outputs

- **Input:** Canonical tool list (from EffectiveToolListBuilder); list of messages in internal format (role, content, optional tool_calls/results).
- **Output:** Structures ready to pass to OLLAMA chat API (e.g. tools array, messages array).

## Acceptance criteria

- Serialized tools are accepted by the OLLAMA API (e.g. /api/chat). Message shape matches what OLLAMA expects (e.g. role, content).
- No hardcoded URLs or credentials; format only.

## References

- Main plan: [§2.2 Base class and representation types](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#22-base-class-and-representation-types), [§2.5.1 Ollama](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#251-ollama) (context size source, tools/messages format).
- Objects and diagrams: [00_objects_and_diagrams.md](00_objects_and_diagrams.md) (OllamaRepresentation).
- Prev: [step_07_context_representation_base.md](step_07_context_representation_base.md). Next: [step_09_redis_message_writer.md](step_09_redis_message_writer.md). Chat flow and step 10 use via registry.

## Success metrics

- **Step-specific:** serialize_tools produces OLLAMA tool format (type "function", function name/description/parameters); serialize_messages produces OLLAMA message shape (role, content); no hardcoded URLs/credentials; OLLAMA models registered in RepresentationRegistry.
- **Standard verification:** No incomplete code, TODO, ellipsis, or syntax issues; no `pass` outside exceptions; no `NotImplemented` outside abstract methods; no deviations from [RULES](../../RULES.md) or plan. After code: `code_mapper -r src`; `mypy src`, `flake8 src tests`, `black src tests` (fix all).

## Comparative analysis vs existing code

| Aspect | Existing | To change | To add |
|--------|----------|-----------|--------|
| Tools | `tools.py` get_ollama_tools() returns list of OLLAMA-format dicts | Can be refactored to use OllamaRepresentation.serialize_tools(canonical_list) when step 06 is wired | OllamaRepresentation: implements ContextRepresentation for OLLAMA API; register in RepresentationRegistry |
| Messages | chat_flow passes messages to OLLAMA as-is | — | serialize_messages() formalizes role/content (and tool_calls if needed) for OLLAMA |

## Dependencies

- Step 07 (base class and registry). Chat flow and context builder (step 10) use this via registry.

## Deliverable

- OllamaRepresentation class; **at startup** populate RepresentationRegistry with all OLLAMA model ids from config (e.g. ollama_models) → OllamaRepresentation, so get_representation(model_id) works for every configured model. Unit tests with example payloads.
