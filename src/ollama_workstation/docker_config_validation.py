"""
Project-specific validation for adapter config
(mTLS, ollama_workstation.ollama_models, commercial model API keys).
Used by docker/run_adapter.py; kept in src for unit testing.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

# Model id prefix -> provider name (for model_providers lookup).
MODEL_PREFIX_TO_PROVIDER: tuple[tuple[str, str], ...] = (
    ("gemini", "google"),
    ("claude", "anthropic"),
    ("gpt-4", "openai"),
    ("gpt-3.5", "openai"),
    ("gpt-35", "openai"),
    ("o1-", "openai"),
    ("o1-mini", "openai"),
    ("grok", "xai"),
    ("deepseek", "deepseek"),
)

# Model id prefix -> required config key for commercial providers (legacy).
COMMERCIAL_PROVIDER_KEY_BY_PREFIX: tuple[tuple[str, str], ...] = (
    ("gemini", "google_api_key"),
    ("claude", "anthropic_api_key"),
    ("gpt-4", "openai_api_key"),
    ("gpt-3.5", "openai_api_key"),
    ("gpt-35", "openai_api_key"),
    ("o1-", "openai_api_key"),
    ("o1-mini", "openai_api_key"),
    ("grok", "xai_api_key"),
    ("deepseek", "deepseek_api_key"),
)

# Provider name (in available_providers list) -> required config key.
# Keys are required only when the provider is in the list of available models/providers.
PROVIDER_TO_CONFIG_KEY: dict[str, str] = {
    "google": "google_api_key",
    "anthropic": "anthropic_api_key",
    "openai": "openai_api_key",
    "xai": "xai_api_key",
    "grok": "xai_api_key",
    "deepseek": "deepseek_api_key",
}

VALID_PROVIDER_NAMES: frozenset[str] = frozenset(
    {"ollama", "google", "anthropic", "openai", "xai", "grok", "deepseek", "openrouter"}
)


def get_provider_for_model(model_id: str) -> str:
    """Return provider name for model_id, or 'ollama' if local."""
    if not model_id or not isinstance(model_id, str):
        return "ollama"
    mid = (model_id or "").strip().lower()
    for prefix, provider in MODEL_PREFIX_TO_PROVIDER:
        if mid.startswith(prefix):
            return provider
    return "ollama"


def get_required_api_key_for_model(model_id: str) -> str | None:
    """
    Return the config key name required for this model (e.g. google_api_key),
    or None if the model is local/Ollama (no commercial key required).
    """
    if not model_id or not isinstance(model_id, str):
        return None
    mid = (model_id or "").strip().lower()
    for prefix, key in COMMERCIAL_PROVIDER_KEY_BY_PREFIX:
        if mid.startswith(prefix):
            return key
    return None


def _collect_providers_in_use(
    ow: dict, ollama_model: str | None, ollama_models: list | None
) -> set[str]:
    """
    Collect provider names that appear in selected models or available_providers.
    When a model is selected, its provider's url and api_key are mandatory.
    """
    providers: set[str] = set()
    model_ids: list[str] = []
    if ollama_model and isinstance(ollama_model, str) and ollama_model.strip():
        model_ids.append(ollama_model.strip())
    if isinstance(ollama_models, list):
        for m in ollama_models:
            if isinstance(m, str) and m.strip():
                model_ids.append(m.strip())
    for mid in model_ids:
        providers.add(get_provider_for_model(mid))
    avail = ow.get("available_providers")
    if isinstance(avail, list):
        for p in avail:
            if isinstance(p, str) and p.strip():
                prov = p.strip().lower()
                if prov in VALID_PROVIDER_NAMES:
                    providers.add(prov)
    return providers


def _collect_required_api_keys(
    ow: dict, ollama_model: str | None, ollama_models: list | None
) -> set[str]:
    """
    Collect config key names required for commercial providers that appear
    in the list of available models (ollama_model, ollama_models) or in
    available_providers. Keys are required only when the provider is present.
    """
    required: set[str] = set()
    model_ids: list[str] = []
    if ollama_model and isinstance(ollama_model, str) and ollama_model.strip():
        model_ids.append(ollama_model.strip())
    if isinstance(ollama_models, list):
        for m in ollama_models:
            if isinstance(m, str) and m.strip():
                model_ids.append(m.strip())
    for mid in model_ids:
        key = get_required_api_key_for_model(mid)
        if key:
            required.add(key)
    avail = ow.get("available_providers")
    if isinstance(avail, list):
        for p in avail:
            if isinstance(p, str) and p.strip():
                prov = p.strip().lower()
                if prov in PROVIDER_TO_CONFIG_KEY:
                    required.add(PROVIDER_TO_CONFIG_KEY[prov])
    return required


def validate_model_providers(
    ow: dict, ollama_model: str | None, ollama_models: list | None
) -> list[str]:
    """
    When a model is selected, url and api_key for its provider are mandatory.
    Uses model_providers (provider -> {url, api_key}) or legacy flat keys.
    Returns list of error messages.
    """
    errors: list[str] = []
    providers = _collect_providers_in_use(ow, ollama_model, ollama_models)
    model_providers = ow.get("model_providers")
    if not isinstance(model_providers, dict):
        model_providers = {}
    provider_urls = ow.get("provider_urls")
    if not isinstance(provider_urls, dict):
        provider_urls = {}

    base_url = (ow.get("ollama_base_url") or "").strip()
    model_server_url = (ow.get("model_server_url") or "").strip()
    ollama_url = base_url or model_server_url

    for prov in providers:
        if prov == "ollama":
            url = ""
            if isinstance(model_providers.get("ollama"), dict):
                url = (model_providers["ollama"].get("url") or "").strip()
            if not url:
                url = ollama_url
            if not url:
                errors.append(
                    "Model ollama selected: model_providers.ollama.url or "
                    "ollama_base_url required"
                )
            continue
        # Commercial: url AND api_key both mandatory when model selected.
        mp = model_providers.get(prov)
        mp = mp if isinstance(mp, dict) else {}
        url = (mp.get("url") or provider_urls.get(prov) or "").strip()
        api_key = (mp.get("api_key") or "").strip()
        if not api_key:
            leg_key = PROVIDER_TO_CONFIG_KEY.get(prov)
            api_key = (ow.get(leg_key) or "").strip() if leg_key else ""
        if not url:
            errors.append(
                "Model %s selected: model_providers.%s.url or provider_urls.%s "
                "required (url bound to model type)" % (prov, prov, prov)
            )
        if not api_key:
            errors.append(
                "Model %s selected: model_providers.%s.api_key or %s "
                "required (key bound to model type)"
                % (prov, prov, PROVIDER_TO_CONFIG_KEY.get(prov, "api_key"))
            )

    return errors


def validate_commercial_model_keys(
    ow: dict, ollama_model: str | None, ollama_models: list | None
) -> list[str]:
    """
    Require API key for each commercial provider that appears in the list of
    available models (ollama_model, ollama_models) or in available_providers.
    Returns list of error messages.
    """
    errors: list[str] = []
    required = _collect_required_api_keys(ow, ollama_model, ollama_models)
    for key in required:
        val = ow.get(key)
        if not val or not (isinstance(val, str) and val.strip()):
            errors.append(
                "Provider in available models requires ollama_workstation.%s "
                "to be set and non-empty" % key
            )
    return errors


def validate_project_config(app_config: dict) -> list[str]:
    """
    Project-specific validation (mTLS, ollama_workstation.ollama_models).
    Returns list of error messages; empty if valid.
    """
    errors: list[str] = []
    server_cfg = app_config.get("server", {})
    proto = str(server_cfg.get("protocol", "http")).lower()
    if proto == "mtls":
        ssl_cfg = server_cfg.get("ssl") or {}
        if not (ssl_cfg.get("cert") and ssl_cfg.get("key")):
            errors.append("mtls requires server.ssl.cert and server.ssl.key")
        transport = app_config.get("transport") or {}
        if not transport.get("verify_client"):
            errors.append("mtls requires transport.verify_client=true")

    ow = app_config.get("ollama_workstation") or {}
    base_url = (ow.get("ollama_base_url") or "").strip()
    model_server_url = (ow.get("model_server_url") or "").strip()
    if not base_url and not model_server_url:
        errors.append("ollama_workstation must set ollama_base_url or model_server_url")
    if model_server_url and not model_server_url.startswith(("http://", "https://")):
        errors.append("ollama_workstation.model_server_url must be http(s) URL")
    # When model selected: url and api_key for its provider are mandatory.
    errors.extend(
        validate_model_providers(
            ow,
            ow.get("ollama_model"),
            ow.get("ollama_models"),
        )
    )
    om = ow.get("ollama_models")
    if om is not None:
        if not isinstance(om, list):
            errors.append("ollama_workstation.ollama_models must be a list")
        else:
            for i, item in enumerate(om):
                if not isinstance(item, str) or not item.strip():
                    errors.append(
                        "ollama_workstation.ollama_models[%s] must be "
                        "non-empty string" % i
                    )
                    break

    # available_providers: optional list of provider names (ollama, google, etc.).
    # If a provider is in this list, the corresponding API key is required.
    avail_prov = ow.get("available_providers")
    if avail_prov is not None:
        if not isinstance(avail_prov, list):
            errors.append("ollama_workstation.available_providers must be a list")
        else:
            for i, p in enumerate(avail_prov):
                if not isinstance(p, str) or not p.strip():
                    errors.append(
                        "ollama_workstation.available_providers[%s] "
                        "must be non-empty string" % i
                    )
                    break
                if p.strip().lower() not in VALID_PROVIDER_NAMES:
                    errors.append(
                        "ollama_workstation.available_providers[%s] must be one of "
                        "%s" % (i, sorted(VALID_PROVIDER_NAMES))
                    )
                    break

    # Commands policy (step 01)
    policy = ow.get("commands_policy")
    if policy is not None:
        if not isinstance(policy, str) or policy not in (
            "allow_by_default",
            "deny_by_default",
        ):
            errors.append(
                "ollama_workstation.commands_policy must be "
                "allow_by_default or deny_by_default"
            )
    for key in ("allowed_commands", "forbidden_commands"):
        val = ow.get(key)
        if val is not None and not isinstance(val, list):
            errors.append("ollama_workstation.%s must be a list" % key)
        elif isinstance(val, list):
            for i, item in enumerate(val):
                if not isinstance(item, str):
                    errors.append(
                        "ollama_workstation.%s[%s] must be a string" % (key, i)
                    )
                    break
    interval = ow.get("command_discovery_interval_sec")
    if interval is not None:
        try:
            val = int(interval)
            if val < 0:
                errors.append(
                    "ollama_workstation.command_discovery_interval_sec must be >= 0"
                )
        except (TypeError, ValueError):
            errors.append(
                "ollama_workstation.command_discovery_interval_sec must be an integer"
            )
    store_type = ow.get("session_store_type")
    if store_type is not None and not isinstance(store_type, str):
        errors.append("ollama_workstation.session_store_type must be a string")
    rport = ow.get("redis_port")
    if rport is not None:
        try:
            if int(rport) < 1 or int(rport) > 65535:
                errors.append("ollama_workstation.redis_port must be 1-65535")
        except (TypeError, ValueError):
            errors.append("ollama_workstation.redis_port must be an integer")
    for key, default in (
        ("max_context_tokens", 4096),
        ("last_n_messages", 10),
        ("min_semantic_tokens", 256),
        ("min_documentation_tokens", 0),
    ):
        val = ow.get(key)
        if val is not None:
            try:
                ival = int(val)
                if ival < 0:
                    errors.append("ollama_workstation.%s must be >= 0" % key)
            except (TypeError, ValueError):
                errors.append("ollama_workstation.%s must be an integer" % key)
    rmode = ow.get("relevance_slot_mode")
    if rmode is not None and rmode not in ("fixed_order", "unified_by_relevance"):
        errors.append(
            "ollama_workstation.relevance_slot_mode must be "
            "fixed_order or unified_by_relevance"
        )
    mdepth = ow.get("max_model_call_depth")
    if mdepth is not None:
        try:
            if int(mdepth) < 0:
                errors.append("ollama_workstation.max_model_call_depth must be >= 0")
        except (TypeError, ValueError):
            errors.append("ollama_workstation.max_model_call_depth must be an integer")
    allow_list = ow.get("model_calling_tool_allow_list")
    if allow_list is not None:
        if not isinstance(allow_list, list):
            errors.append(
                "ollama_workstation.model_calling_tool_allow_list must be a list"
            )
        else:
            for i, item in enumerate(allow_list):
                if not isinstance(item, str):
                    errors.append(
                        "ollama_workstation.model_calling_tool_allow_list[%s] "
                        "must be a string" % i
                    )
                    break
    if ow.get("redis_host") is not None and not isinstance(ow.get("redis_host"), str):
        errors.append("ollama_workstation.redis_host must be a string")
    cname = ow.get("model_server_container_name")
    cimg = ow.get("model_server_image")
    if cname is not None and not isinstance(cname, str):
        errors.append("ollama_workstation.model_server_container_name must be a string")
    if cimg is not None and not isinstance(cimg, str):
        errors.append("ollama_workstation.model_server_image must be a string")
    if (
        cname
        and isinstance(cname, str)
        and cname.strip()
        and (not cimg or not str(cimg).strip())
    ):
        errors.append(
            "ollama_workstation.model_server_container_name requires model_server_image"
        )
    if ow.get("redis_key_prefix") is not None and not isinstance(
        ow.get("redis_key_prefix"), str
    ):
        errors.append("ollama_workstation.redis_key_prefix must be a string")
    mp = ow.get("model_providers")
    if mp is not None:
        if not isinstance(mp, dict):
            errors.append("ollama_workstation.model_providers must be a dict")
        else:
            for prov, cfg in mp.items():
                if not isinstance(prov, str) or not prov.strip():
                    continue
                if not isinstance(cfg, dict):
                    errors.append(
                        "ollama_workstation.model_providers.%s must be "
                        "{url, api_key}" % prov
                    )
                else:
                    u = (cfg.get("url") or "").strip()
                    k = (cfg.get("api_key") or "").strip()
                    if prov != "ollama" and u and not k:
                        errors.append(
                            "ollama_workstation.model_providers.%s: api_key "
                            "required when url set (mandatory for selected model)"
                            % prov
                        )
    for key in (
        "ollama_api_key",
        "google_api_key",
        "anthropic_api_key",
        "openai_api_key",
        "xai_api_key",
        "deepseek_api_key",
        "openrouter_api_key",
    ):
        val = ow.get(key)
        if val is not None and not isinstance(val, str):
            errors.append("ollama_workstation.%s must be a string" % key)
        elif isinstance(val, str) and not val.strip():
            errors.append("ollama_workstation.%s must be non-empty when set" % key)
    return errors
