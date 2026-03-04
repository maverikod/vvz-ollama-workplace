# Context representation layer: analysis

**Author:** Vasiliy Zdanovskiy  
**Email:** vasilyvz@gmail.com  

The project is conceived as a **unified model workstation**: one adapter that can talk to different model backends (Ollama today; others later). The **output** of the workstation—what is sent to the model and how tool results are formatted—must depend on the **model/API type**. That is implemented as a dedicated **context representation layer**.

---

## 1. Where the layer lives

| Component | Role |
|-----------|------|
| **ContextRepresentation** (`context_representation.py`) | Abstract base: `serialize_tools`, `serialize_messages`, `format_tool_result`. One subclass per provider (Ollama, future: Gemini, OpenAI, etc.). |
| **RepresentationRegistry** (`representation_registry.py`) | Maps `model_id` → `ContextRepresentation`. Used to select the representation for the session’s model. |
| **OllamaRepresentation** (`ollama_representation.py`) | Implements OLLAMA format: tools as `type: "function"`, `function: { name, description, parameters }`; messages with `role`, `content`; tool result as JSON string. |
| **ContextBuilder** (`context_builder.py`) | Builds ordered context (standards, rules, last N, relevance slot), then calls `representation.serialize_messages(ordered)` for the final list. |
| **chat_flow** (`chat_flow.py`) | Gets representation via `registry.get_representation(use_model)`; uses it to serialize tools and to `format_tool_result(raw)` for tool message content. |
| **get_model_context** command | Same pipeline as ollama_chat: uses registry to get representation and serialize messages + tools for the session’s model. |

So: **one class per model/API type** (ContextRepresentation subclass), **one registry** (model_id → representation), and **one place** where the “shape” of the payload is decided: the representation’s `serialize_*` and `format_tool_result`.

---

## 2. Data flow

1. **Canonical internal format**  
   Messages and tool list are kept in a provider-agnostic form (e.g. list of messages with `role`, `content`; list of `(display_name, CommandSchema)`).

2. **Per-request**  
   For a given session (and thus `model_id`), the registry returns the right representation.  
   **ContextBuilder** uses it to serialize the ordered message list.  
   **chat_flow** uses it to serialize tools and to convert each raw tool result into the string the model expects.

3. **Output**  
   The “output” of the workstation toward the model is exactly:  
   - **Messages**: `representation.serialize_messages(...)`  
   - **Tools**: `representation.serialize_tools(...)`  
   - **Tool message content**: `representation.format_tool_result(raw)`  

So the **separate layer that forms the context representation depending on model type** is: **ContextRepresentation + RepresentationRegistry + per-model registration**. It is already in place; currently only **Ollama** is implemented.

---

## 3. Adding another model type

To support a new backend (e.g. Gemini, OpenAI):

1. Add a new subclass of **ContextRepresentation** (e.g. `GeminiRepresentation`) in a new file.
2. Implement `serialize_tools`, `serialize_messages`, `format_tool_result` according to that API.
3. Register it in **RepresentationRegistry** for the corresponding `model_id`(s) (e.g. in the same place where `register_ollama_models` is called, or a similar registration path).

No change is required in **chat_flow**, **ContextBuilder**, or discovery logic—they already use the registry and the abstract interface.

---

## 4. Summary

- The **unified workstation** output is **provider-specific** only via this representation layer.
- The **layer** is: **ContextRepresentation** (base) + **RepresentationRegistry** (model_id → representation) + **OllamaRepresentation** (and future subclasses).
- **ContextBuilder** and **chat_flow** are **provider-agnostic**; they call the representation chosen by model_id.  
- To support a new model type: add one **ContextRepresentation** subclass and register it for the new model_id(s).
