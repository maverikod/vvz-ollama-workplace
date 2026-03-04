# Step 07: Context representation base and registry

**Author:** Vasiliy Zdanovskiy  
**Email:** vasilyvz@gmail.com  

**Scope:** Define the base class for context/tool representation and the registry that maps model id to representation type. One step = one file (this doc).

## Goal

- **ContextRepresentation** (abstract base): methods to serialize tools and messages in a provider-specific format (e.g. serialize_tools(tool_list) -> list/dict for API; serialize_messages(messages) -> list for API). Optional: max_context_tokens() or similar.
- **RepresentationRegistry:** model_id (or model family) -> ContextRepresentation type or instance. When building a request for a session, session.model is used to select the representation; that representation serializes tools and messages for the actual API call.
- On session model change, the same context (trimmed if needed) is serialized with the new model’s representation (see main plan §2).

## Objects

- **ContextRepresentation:** Abstract base with serialize_tools(tool_list), serialize_messages(messages), format_tool_result(raw_result) → standard form (e.g. tool message content); optional max_context_tokens().
- **RepresentationRegistry:** get_representation(model_id) -> ContextRepresentation. Populated from config or code (model_id -> class or instance).

## Inputs / outputs

- **Input (registry):** model_id string (e.g. from session.model).
- **Output (registry):** ContextRepresentation instance for that model (or default/fallback if unknown).
- **Input (representation):** Canonical tool list; list of messages; raw tool result (from canonical layer).
- **Output (representation):** Provider-specific payload (tools array, messages format); format_tool_result(raw) → string (tool message content).

## Acceptance criteria

- Unknown model_id returns a sensible default (e.g. Ollama representation) or raises with a clear error.
- Base class does not depend on any specific provider; concrete implementations (step 08 and later) implement the interface.

## References

- Main plan: [§2.2 Base class and representation types](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#22-base-class-and-representation-types), [§2.4 Summary (context representation)](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#24-summary-context-representation), [§2.5 Per-model scheme (Ollama and Google)](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#25-per-model-scheme-context-size-and-representation-ollama-and-google) for context size and representation details.
- Objects and diagrams: [00_objects_and_diagrams.md](00_objects_and_diagrams.md) (ContextRepresentation, RepresentationRegistry).
- Prev: [step_06_effective_tool_list.md](step_06_effective_tool_list.md). Next: [step_08_ollama_representation.md](step_08_ollama_representation.md). Step 08 implements OllamaRepresentation; step 10 uses registry.

## Success metrics

- **Step-specific:** ContextRepresentation abstract: serialize_tools(tool_list), serialize_messages(messages); optional max_context_tokens(); RepresentationRegistry get_representation(model_id); unknown model_id returns default or clear error; base has no provider-specific code.
- **Standard verification:** No incomplete code, TODO, ellipsis, or syntax issues; no `pass` except in ABC stubs (use NotImplemented in abstract methods); no `NotImplemented` outside abstract methods; no deviations from [RULES](../../RULES.md) or plan. After code: `code_mapper -r src`; `mypy src`, `flake8 src tests`, `black src tests` (fix all).

## Comparative analysis vs existing code

| Aspect | Existing | To change | To add |
|--------|----------|-----------|--------|
| Tool format | `tools.py`: OLLAMA-style tools (type "function", name, description, parameters) | — | ContextRepresentation.serialize_tools() for provider-agnostic input → provider-specific output; registry model_id → representation |
| Messages | chat_flow builds message list for OLLAMA | — | serialize_messages(messages) in base; per-provider in step 08+ |

## Extensibility: adding new model types

**Adding a new model type is done by adding a single subclass of ContextRepresentation and registering it.**

1. Implement a new class that inherits from **ContextRepresentation** and implements:
   - **serialize_tools(tool_list)** — canonical tool list → provider-specific tools array.
   - **serialize_messages(messages)** — canonical messages → provider-specific messages format.
   - **format_tool_result(raw_result)** — raw tool result → tool message content string for this provider.
   - Optionally **max_context_tokens(model_id)**.
2. Register the instance (or class) in **RepresentationRegistry** for the relevant model_id(s) (e.g. from config).
3. No changes to chat_flow, discovery, or registry logic: they call the representation selected by session.model. New model types are plugged in by adding one descendant class and registration.

## Dependencies

- None for base and registry. Step 08 implements OllamaRepresentation; step 10 uses registry when building context.

## Deliverable

- ContextRepresentation ABC; RepresentationRegistry class and registration of at least one representation type (e.g. Ollama). Unit tests with a minimal concrete representation.
