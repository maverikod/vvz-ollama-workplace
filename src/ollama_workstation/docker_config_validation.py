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
    return errors
