"""
Generate client config for connecting to model workspace server.

Builds on adapter config contract: produces adapter-compatible JSON with client
section (TLS, endpoint) and model_workspace_client section (WS endpoint,
auth/TLS, retries, timeouts, observability). Usable as independent package
runtime input.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import json
import os
from pathlib import Path
from typing import Any


def _default_client_template(certs_dir: Path) -> dict[str, Any]:
    """Default settings template for model workspace client."""
    return {
        "output_path": None,
        "certs_dir": str(certs_dir),
        "ws_endpoint": "wss://model-workspace-server:8016",
        "client_cert_file": str(certs_dir / "client" / "mcp-proxy.crt"),
        "client_key_file": str(certs_dir / "client" / "mcp-proxy.key"),
        "ca_cert_file": str(certs_dir / "ca" / "ca.crt"),
        "connect_timeout_seconds": 30,
        "request_timeout_seconds": 120,
        "retry_max_attempts": 3,
        "retry_backoff_seconds": 2.0,
        "log_level": "INFO",
        "metrics_enabled": False,
    }


def _env_overlay() -> dict[str, Any]:
    """Build overlay from environment (env-driven generation)."""
    certs_dir = os.environ.get("CERTS_DIR", "")
    out: dict[str, Any] = {}
    if certs_dir:
        p = Path(certs_dir)
        out["certs_dir"] = certs_dir
        out["client_cert_file"] = str(p / "client" / "mcp-proxy.crt")
        out["client_key_file"] = str(p / "client" / "mcp-proxy.key")
        out["ca_cert_file"] = str(p / "ca" / "ca.crt")
    out["output_path"] = os.environ.get("MODEL_WORKSPACE_CLIENT_CONFIG_PATH") or ""
    out["ws_endpoint"] = os.environ.get("MODEL_WORKSPACE_WS_ENDPOINT") or ""
    ct = os.environ.get("MODEL_WORKSPACE_CLIENT_CONNECT_TIMEOUT")
    if ct:
        try:
            out["connect_timeout_seconds"] = int(ct)
        except ValueError:
            pass
    rt = os.environ.get("MODEL_WORKSPACE_CLIENT_REQUEST_TIMEOUT")
    if rt:
        try:
            out["request_timeout_seconds"] = int(rt)
        except ValueError:
            pass
    out["log_level"] = os.environ.get("MODEL_WORKSPACE_CLIENT_LOG_LEVEL") or ""
    return out


def merge_settings(
    template: dict[str, Any],
    env_overlay: dict[str, Any] | None = None,
    args_overlay: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Merge template with optional env and args overlays.

    Later keys override earlier: template < env_overlay < args_overlay.
    """
    out: dict[str, Any] = dict(template)
    if env_overlay:
        for k, v in env_overlay.items():
            if v is not None and v != "":
                out[k] = v
    if args_overlay:
        for k, v in args_overlay.items():
            if v is not None and v != "":
                out[k] = v
    return out


def generate_client_config(settings: dict[str, Any]) -> None:
    """
    Generate adapter-compatible client config for model workspace server.

    Writes JSON to settings["output_path"] with:
    - client: enabled, protocol mtls, ssl (cert, key, ca)
    - model_workspace_client: ws_endpoint, auth/TLS paths, retries, timeouts,
      observability (log_level, metrics_enabled).

    Required keys: output_path, certs_dir (or client_cert_file, client_key_file,
    ca_cert_file), ws_endpoint.
    Optional: connect_timeout_seconds, request_timeout_seconds, retry_max_attempts,
    retry_backoff_seconds, log_level, metrics_enabled.
    """
    out_path = settings.get("output_path")
    if out_path is None:
        raise ValueError("output_path is required")
    out_path = Path(out_path)
    certs_dir = Path(settings["certs_dir"])
    ws_endpoint = str(settings.get("ws_endpoint", "")).strip()
    if not ws_endpoint:
        raise ValueError("ws_endpoint is required")

    client_cert = str(
        settings.get("client_cert_file") or certs_dir / "client" / "mcp-proxy.crt"
    )
    client_key = str(
        settings.get("client_key_file") or certs_dir / "client" / "mcp-proxy.key"
    )
    ca_crt = str(settings.get("ca_cert_file") or certs_dir / "ca" / "ca.crt")

    connect_timeout = int(settings.get("connect_timeout_seconds", 30))
    request_timeout = int(settings.get("request_timeout_seconds", 120))
    retry_max = int(settings.get("retry_max_attempts", 3))
    retry_backoff = float(settings.get("retry_backoff_seconds", 2.0))
    log_level = str(settings.get("log_level", "INFO"))
    metrics_enabled = bool(settings.get("metrics_enabled", False))

    out_path.parent.mkdir(parents=True, exist_ok=True)

    data: dict[str, Any] = {
        "client": {
            "enabled": True,
            "protocol": "mtls",
            "ssl": {
                "cert": client_cert,
                "key": client_key,
                "ca": ca_crt,
                "crl": None,
                "dnscheck": False,
                "check_hostname": None,
            },
        },
        "server_validation": {
            "enabled": False,
            "protocol": "http",
            "ssl": None,
            "timeout": 10,
            "use_token": False,
            "use_roles": False,
            "tokens": {},
            "roles": {},
            "auth_header": "X-API-Key",
            "roles_header": "X-Roles",
            "health_path": "/health",
            "check_hostname": False,
        },
        "auth": {
            "use_token": False,
            "use_roles": False,
            "tokens": {},
            "roles": {},
        },
        "model_workspace_client": {
            "ws_endpoint": ws_endpoint,
            "client_cert_file": client_cert,
            "client_key_file": client_key,
            "ca_cert_file": ca_crt,
            "connect_timeout_seconds": connect_timeout,
            "request_timeout_seconds": request_timeout,
            "retry_max_attempts": retry_max,
            "retry_backoff_seconds": retry_backoff,
            "observability": {
                "log_level": log_level,
                "metrics_enabled": metrics_enabled,
            },
        },
    }

    out_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def generate_from_merged(
    template: dict[str, Any] | None = None,
    env_overlay: dict[str, Any] | None = None,
    args_overlay: dict[str, Any] | None = None,
) -> None:
    """
    Generate client config from merged template, env overlay, and args overlay.

    If template is None, uses default template with certs_dir from env or cwd.
    """
    certs_dir = Path(
        (args_overlay or {}).get("certs_dir")
        or (env_overlay or {}).get("certs_dir")
        or os.environ.get("CERTS_DIR", "mtls_certificates")
    )
    tpl = template or _default_client_template(certs_dir)
    env = env_overlay if env_overlay is not None else _env_overlay()
    args = args_overlay or {}
    settings = merge_settings(tpl, env, args)
    if not settings.get("output_path"):
        settings["output_path"] = Path("config") / "model_workspace_client_config.json"
    generate_client_config(settings)
