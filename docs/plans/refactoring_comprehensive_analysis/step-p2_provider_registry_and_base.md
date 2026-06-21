# STEP-P2 — Provider registry + base contract enforcement (fix P2 + P3)

**Concern:** `provider_registry.py`, `OllamaServerChatCommand`, `OllamaServerEmbedCommand`
**Issues:** P2 (get_client NOT IMPL for 5 providers), P3 (direct HTTP bypasses contract)
**Severity:** 🔴 High
**Depends on:** STEP-08 (BaseProviderClient is proper ABC)
**Blocks:** STEP-I1..I5, STEP-06, STEP-07

---

## Task

### P2a. Implement provider_registry.get_client() for all 6 providers

```python
def get_client(provider_name: str, config: ProviderClientConfig) -> BaseProviderClient:
    clients = {
        "ollama":    lambda: OllamaProviderClient(config.providers["ollama"]),
        "openai":    lambda: OpenAIProviderClient(config.providers["openai"]),
        "anthropic": lambda: AnthropicProviderClient(config.providers["anthropic"]),
        "google":    lambda: GoogleProviderClient(config.providers["google"]),
        "xai":       lambda: XAIProviderClient(config.providers["xai"]),
        "deepseek":  lambda: DeepSeekProviderClient(config.providers["deepseek"]),
    }
    if provider_name not in clients:
        raise ValidationError(f"Unknown provider: {provider_name}")
    if provider_name not in config.providers:
        raise ValidationError(f"Provider '{provider_name}' not configured")
    return clients[provider_name]()
```

Each lambda is only called if the provider is configured — missing section
raises `ValidationError` (from `provider_errors.py`), not `KeyError`.

### P2b. Remove OllamaServerChatCommand and OllamaServerEmbedCommand

Both commands bypass `BaseProviderClient` and make raw HTTP to Ollama.
They must be **removed** (or deprecated) because:
- `chat` is covered by `OllamaChatCommand` which uses `OllamaProviderClient.chat()`
- `embed` is covered by `VectorizationClient` (Path A/B per REQUIREMENTS §3)

If low-level Ollama diagnostics are needed, create
`OllamaRawCommand(BaseCommand)` (not a provider client) clearly marked
as diagnostic-only, not part of the provider abstraction.

### P2c. Fix _build_ollama() import

Replace broken `ollama_provider_client` package import with direct
`from .ollama_provider_client import OllamaProviderClient`.

## Acceptance criteria

- [ ] `get_client()` works for all 6 provider names
- [ ] `get_client("unknown", ...)` raises `ValidationError`
- [ ] `OllamaServerChatCommand` and `OllamaServerEmbedCommand` removed
  (or replaced by diagnostic command not in provider path)
- [ ] `OllamaProviderClient` imported correctly
- [ ] `list_supported_providers()` returns all 6 names
- [ ] `lint_code` + `type_check_code` pass
