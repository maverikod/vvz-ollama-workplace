# ollama_provider_client

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

Provider client for **Ollama**: implements root [provider_client_standard](../../docs/standards/provider_client_standard.md). For the model workspace, **Ollama server is just a separate provider**; this package is the client that talks to ollama-adapter (or directly to Ollama). PyPI-publishable.

**Structure:** `docs/` (ТЗ, reports/, plans/), `src/ollama_provider_client/`, `tests/` (unit/, integration/), `config/`, `examples/`, `code_analysis/` (generated), `projectid`, `pyproject.toml`, `.gitignore`.

**ТЗ:** `docs/ТЗ.md`. Context: root [SPEC](../../docs/plans/refactoring_adapter_structure/SPEC.md); [provider_client_standard](../../docs/standards/provider_client_standard.md).
