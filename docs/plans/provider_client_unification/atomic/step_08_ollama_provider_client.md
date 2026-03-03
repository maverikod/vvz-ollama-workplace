<!--
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
-->

# Step 08: Ollama Provider Client

## Target file

- `src/ollama_workstation/ollama_provider_client.py` (canonical path in [SCOPE_FREEZE.md](SCOPE_FREEZE.md)). Migration of existing Ollama usage: see [SCOPE_FREEZE.md](SCOPE_FREEZE.md) § Ollama migration.

## Dependencies

- [SCOPE_FREEZE.md](SCOPE_FREEZE.md)
- [step_01_client_standard_document.md](step_01_client_standard_document.md)
- [step_03_uniform_error_model.md](step_03_uniform_error_model.md)
- [step_04_abstract_base_class.md](step_04_abstract_base_class.md)
- [../QUALITY_GATE.md](../QUALITY_GATE.md)
- [../CLIENT_UNIFICATION_TZ.md](../CLIENT_UNIFICATION_TZ.md) (FR-2: Ollama as first-class provider; provider-specific transport/auth stays inside client)

## Detailed scope

- Implement concrete Ollama provider client that subclasses the abstract base from step_04.
- All methods implemented: validate_config, healthcheck, chat, embed, supports_tools, normalize_response, map_error.
- Capability flags set correctly (e.g. supports_embeddings per Ollama capability); embed contract: if unsupported, flag False and embed() raises defined error.
- Transport/auth/format details internal to this client; workstation sees only the common API.
- No direct redis/ollama bypass; use only provider endpoint for model communication.

## Success metric

- Ollama client implements full contract; passes validation and healthcheck for valid config.
- Chat (and embed when supported) work against Ollama endpoint; errors normalized via map_error.
- Workstation can use this client as the single path for Ollama model communication.

## Blocking protocol (mandatory)

- If any requirement is unclear, contradictory, or underspecified: **STOP** implementation.
- Ask a clarifying question and proceed only after explicit clarification.
