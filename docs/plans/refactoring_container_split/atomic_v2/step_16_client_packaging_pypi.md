# Step 16: Independent Client Packaging for PyPI

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

## Target file
- `pyproject.toml`

## Dependencies
- `NAMING_FREEZE.md` (mandatory naming/source of truth)
- `../QUALITY_GATE.md`

## Detailed scope
- Define independent packaging strategy for `model_workspace_client` and `database_client`.
- Use frozen PyPI names from `NAMING_FREEZE.md`:
  - `model_workspace_client` -> `model-workspace-client`
  - `database_client` -> `ollama-model-database-client`
- Ensure standalone build/install/publication workflow.

## Success metric
- Each client package can be built and installed independently from artifacts.

## Blocking protocol (mandatory)
- If any requirement is unclear, contradictory, or underspecified: **STOP** implementation.
- Ask a clarifying question and proceed only after explicit clarification.
