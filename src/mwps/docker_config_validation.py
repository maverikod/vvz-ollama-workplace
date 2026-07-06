"""
Project-specific validation for adapter config
(mTLS, mwps, provider_clients for model-workspace).
Used by docker/run_adapter.py; kept in src for unit testing.
Model-workspace: only provider_clients as provider source; legacy fields rejected.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from mwps.provider_client_config_validator import (
    validate_config_provider_clients,
)

# Legacy provider fields forbidden for model-workspace (provider_clients only).
LEGACY_FLAT_API_KEYS: frozenset[str] = frozenset(
    {
        "google_api_key",
        "anthropic_api_key",
        "openai_api_key",
        "xai_api_key",
        "deepseek_api_key",
        "openrouter_api_key",
        "mwps_api_key",
    }
)


def _get_mwps_from_ow(ow: dict) -> dict | None:
    """
    Read mwps settings from mwps.mwps section only.
    Returns dict with normalized keys or None if section missing/invalid.
    """
    section = ow.get("mwps")
    if not isinstance(section, dict):
        return None
    base = (section.get("base_url") or "").strip()
    msurl = (section.get("model_server_url") or section.get("base_url") or "").strip()
    return {
        "mwps_base_url": base,
        "model_server_url": msurl or base,
        "mwps_model": (section.get("model") or "").strip(),
        "mwps_models": (
            section.get("models") if isinstance(section.get("models"), list) else []
        ),
    }


def get_provider_for_model(model_id: str) -> str:
    """
    Return provider name for model_id.

    Only 'mwps' is currently supported by the provider client registry;
    direct commercial provider routing by model-id prefix was removed
    (commercial LLM access is delegated to model-access-core, a separate
    reorientation step).
    """
    return "mwps"


def validate_project_config(app_config: dict) -> list[str]:
    """
    Project-specific validation (mTLS, mwps.mwps).
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

    # Model-workspace: provider_clients only; no legacy provider fields.
    ow = app_config.get("mwps") or {}
    pc = app_config.get("provider_clients")
    if not pc or not isinstance(pc, dict):
        errors.append(
            "provider_clients is required for model-workspace; "
            "no autogeneration from legacy fields."
        )
    else:
        pc_errors = validate_config_provider_clients(app_config)
        for path, msg in pc_errors:
            errors.append("%s: %s" % (path, msg))
    if ow.get("model_providers") is not None:
        errors.append(
            "mwps.model_providers is forbidden for model-workspace; "
            "use provider_clients only."
        )
    if ow.get("provider_urls") is not None:
        errors.append(
            "mwps.provider_urls is forbidden for model-workspace; "
            "use provider_clients only."
        )
    for leg_key in LEGACY_FLAT_API_KEYS:
        if ow.get(leg_key) is not None:
            errors.append(
                "mwps.%s is forbidden for model-workspace; "
                "use provider_clients only." % leg_key
            )

    oo = _get_mwps_from_ow(ow)
    if oo is None:
        errors.append("mwps.mwps is required and must be an object")
    else:
        raw_om = (ow.get("mwps") or {}).get("models")
        om = oo["mwps_models"]
        if raw_om is not None and not isinstance(raw_om, list):
            errors.append("mwps.mwps.models must be a list")
        elif om:
            for i, item in enumerate(om):
                if not isinstance(item, str) or not item.strip():
                    errors.append(
                        "mwps.mwps.models[%s] must be " "non-empty string" % i
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
                "mwps.commands_policy must be " "allow_by_default or deny_by_default"
            )
    for key in ("allowed_commands", "forbidden_commands"):
        val = ow.get(key)
        if val is not None and not isinstance(val, list):
            errors.append("mwps.%s must be a list" % key)
        elif isinstance(val, list):
            for i, item in enumerate(val):
                if not isinstance(item, str):
                    errors.append("mwps.%s[%s] must be a string" % (key, i))
                    break
    interval = ow.get("command_discovery_interval_sec")
    if interval is not None:
        try:
            val = int(interval)
            if val < 0:
                errors.append("mwps.command_discovery_interval_sec must be >= 0")
        except (TypeError, ValueError):
            errors.append("mwps.command_discovery_interval_sec must be an integer")
    store_type = ow.get("session_store_type")
    if store_type is not None and not isinstance(store_type, str):
        errors.append("mwps.session_store_type must be a string")
    rport = ow.get("redis_port")
    if rport is not None:
        try:
            if int(rport) < 1 or int(rport) > 65535:
                errors.append("mwps.redis_port must be 1-65535")
        except (TypeError, ValueError):
            errors.append("mwps.redis_port must be an integer")
    for key, default in (
        ("max_context_tokens", 4096),
        ("last_n_messages", 10),
        ("min_documentation_tokens", 0),
    ):
        val = ow.get(key)
        if val is not None:
            try:
                ival = int(val)
                if ival < 0:
                    errors.append("mwps.%s must be >= 0" % key)
            except (TypeError, ValueError):
                errors.append("mwps.%s must be an integer" % key)
    mdepth = ow.get("max_model_call_depth")
    if mdepth is not None:
        try:
            if int(mdepth) < 0:
                errors.append("mwps.max_model_call_depth must be >= 0")
        except (TypeError, ValueError):
            errors.append("mwps.max_model_call_depth must be an integer")
    allow_list = ow.get("model_calling_tool_allow_list")
    if allow_list is not None:
        if not isinstance(allow_list, list):
            errors.append("mwps.model_calling_tool_allow_list must be a list")
        else:
            for i, item in enumerate(allow_list):
                if not isinstance(item, str):
                    errors.append(
                        "mwps.model_calling_tool_allow_list[%s] " "must be a string" % i
                    )
                    break
    if ow.get("redis_host") is not None and not isinstance(ow.get("redis_host"), str):
        errors.append("mwps.redis_host must be a string")
    if ow.get("redis_key_prefix") is not None and not isinstance(
        ow.get("redis_key_prefix"), str
    ):
        errors.append("mwps.redis_key_prefix must be a string")
    return errors
