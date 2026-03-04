# Step 11: Documentation source interface and slot builder

**Author:** Vasiliy Zdanovskiy  
**Email:** vasilyvz@gmail.com  

**Scope:** Define the DocumentationSource interface (TOC + get content) and at least one backend (e.g. directory); DocumentationSlotBuilder for filling the doc block (canon first, then clarifications). One step = one file (this doc).

## Goal

- **DocumentationSource** (interface): list_items(session_id?) -> TOC (list of items with id, title, short description, canon vs clarification); get_content(item_id) -> text. Same interface for pre-filling the doc block and for the standardized documentation tool used by the model during the dialogue.
- **DocumentationSlotBuilder:** Fills the documentation slot: reserve min_documentation_tokens if configured; add canon items first, then clarifications; use DocumentationSource and optional relevance ranking.
- At least one **backend** implementation: e.g. directory backend (list files under docs_path, return content by path). Optional: vector DB backend later.

## Objects

- **DocumentationSource:** Abstract or protocol: list_items(session_id: Optional[str]) -> list of TOC entries; get_content(item_id: str) -> str.
- **DocumentationSlotBuilder:** build(current_message, session_id, remainder_tokens, config) -> list of doc content segments (or structured blocks). Uses DocumentationSource; applies canon-first then clarifications; may use relevance (same embedding as relevance slot) if unified.
- **DirectoryDocumentationSource** (example): list_items lists files under config docs_path; get_content reads file by path/id.

## Inputs / outputs

- **Input (source):** session_id (optional); item_id or path for get_content.
- **Output (source):** TOC list; raw text for get_content.
- **Input (slot builder):** current message, session_id, token budget, config (min_documentation_tokens, relevance mode).
- **Output (slot builder):** Ordered doc content for the context window (or for tool response).

## Acceptance criteria

- Model (or context builder) can call TOC then request specific content; no dependency on provider-specific APIs in the interface.
- Config: backend type and connection (e.g. docs_path for directory). Tool names (e.g. documentation_toc, documentation_content) standardized.

## References

- Main plan: [§4.4a–4.4c Documentation block and access](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#44a-documentation-block-canon-and-clarifications), [§4.4e External data sources and priority](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#44e-external-data-sources-in-the-documentation-part-of-context-priority), [§4.4f Databases and Database manager](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#44f-databases-and-database-manager-chunk_metadata_adapter-as-glue), [§3.5.3 External Database (capability descriptor)](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#353-external-database-capability-descriptor), [§4.5 Config (context)](../DYNAMIC_COMMANDS_AND_MEMORY_PLAN.md#45-config-context).
- Objects and diagrams: [00_objects_and_diagrams.md](00_objects_and_diagrams.md) (DocumentationSource, DocumentationSlotBuilder, Database, DatabaseManager).
- Prev: [step_10_context_builder.md](step_10_context_builder.md). Next: [step_12_call_stack_and_depth.md](step_12_call_stack_and_depth.md). Context builder (step 10) and doc tools consume this.

## Success metrics

- **Step-specific:** DocumentationSource: list_items(session_id?), get_content(item_id); DocumentationSlotBuilder: canon first then clarifications; at least one backend (e.g. directory); config backend type and connection; tool names (e.g. documentation_toc, documentation_content) standardized.
- **Standard verification:** No incomplete code, TODO, ellipsis, or syntax issues; no `pass` outside exceptions; no `NotImplemented` outside abstract methods; no deviations from [RULES](../../RULES.md) or plan. After code: `code_mapper -r src`; `mypy src`, `flake8 src tests`, `black src tests` (fix all).

## Comparative analysis vs existing code

| Aspect | Existing | To change | To add |
|--------|----------|-----------|--------|
| Docs | No documentation source or slot | — | DocumentationSource (interface); DirectoryDocumentationSource (e.g. docs_path); DocumentationSlotBuilder; config docs_path / backend |
| Context | Step 10 relevance slot | Step 10 can use DocumentationSlotBuilder for doc block | — |
| **Config generator / validator** | — | — | When adding documentation source config (e.g. docs_path, backend type): update generator overlay and `validate_project_config` per main plan §6.4 (adapter first, project on top). |

## Dependencies

- Optional step 10 (relevance slot) for unified ranking of doc chunks. Context builder (step 10) and documentation tools consume this.

## Deliverable

- DocumentationSource interface; DirectoryDocumentationSource (or equivalent); DocumentationSlotBuilder. Config and unit tests.
- **Optional / later:** Integration with **external data sources** (§4.4e): Database (semantic + full-text + filter-by-pattern; capability metric), DatabaseManager (add, remove, get by filter). Documentation slot can be filled from multiple sources with **priority**; flow: collect → rank by vector similarity → apply source priority. Query/filter contract via **chunk_metadata_adapter** (ChunkQuery, FilterParser, FILTER_GRAMMAR) as glue between projects.
