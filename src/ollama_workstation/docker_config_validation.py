"""
Project-specific validation for adapter config
(mTLS, ollama_workstation.ollama_models).
Used by docker/run_adapter.py; kept in src for unit testing.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""


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
    return errors
