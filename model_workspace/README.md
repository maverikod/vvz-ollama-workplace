# model_workspace

**Author:** Vasiliy Zdanovskiy  
**email:** vasilyvz@gmail.com

Model workspace subproject: Agent Workstation application using **provider clients** (ollama_provider_client, redis_provider_client). For the model workspace, **Ollama server is just a separate provider**. No Redis or Ollama inside. PyPI-publishable layout.

**Structure (per project standard):** `docs/` (ТЗ, reports/, plans/), `docker/` (build_image.sh, run_container.sh), `src/model_workspace/`, `tests/` (unit/, integration/), `config/`, `examples/`, `code_analysis/` (generated), `projectid`, `pyproject.toml`, `.gitignore`.

**ТЗ подпроекта:** `docs/ТЗ.md`. Общий контекст: корень репозитория `docs/plans/refactoring_adapter_structure/SPEC.md`.
