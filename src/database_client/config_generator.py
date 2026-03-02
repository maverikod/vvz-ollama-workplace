"""
Generate DB client config with endpoint/auth/TLS/retry configuration.

Builds on adapter config contract: generates client config with client (TLS),
server_validation, auth, and database_client section (base_url, certs, retries,
timeouts, observability). Single adapter config format, consumable by
standalone database_client package. Contract compatible with database server
config schema (mTLS, same top-level sections).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import json
import os
from pathlib import Path
from typing import Any


def _default_client_template(certs_dir: Path) -> dict[str, Any]:
    """Default settings template for database client."""
    return {
        "output_path": None,
        "certs_dir": str(certs_dir),
        "base_url": "https://database-server:8017",
        "client_cert_file": str(certs_dir / "client" / "chunk-writer.crt"),
        "client_key_file": str(certs_dir / "client" / "chunk-writer.key"),
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
        out["client_cert_file"] = str(p / "client" / "chunk-writer.crt")
        out["client_key_file"] = str(p / "client" / "chunk-writer.key")
        out["ca_cert_file"] = str(p / "ca" / "ca.crt")
    out["output_path"] = os.environ.get("DATABASE_CLIENT_CONFIG_PATH") or ""
    out["base_url"] = os.environ.get("DATABASE_CLIENT_BASE_URL") or ""
    ct = os.environ.get("DATABASE_CLIENT_CONNECT_TIMEOUT")
    if ct:
        try:
            out["connect_timeout_seconds"] = int(ct)
        except ValueError:
            pass
    rt = os.environ.get("DATABASE_CLIENT_REQUEST_TIMEOUT")
    if rt:
        try:
            out["request_timeout_seconds"] = int(rt)
        except ValueError:
            pass
    retry_max = os.environ.get("DATABASE_CLIENT_RETRY_MAX_ATTEMPTS")
    if retry_max:
        try:
            out["retry_max_attempts"] = int(retry_max)
        except ValueError:
            pass
    retry_backoff = os.environ.get("DATABASE_CLIENT_RETRY_BACKOFF_SECONDS")
    if retry_backoff:
        try:
            out["retry_backoff_seconds"] = float(retry_backoff)
        except ValueError:
            pass
    metrics = os.environ.get("DATABASE_CLIENT_METRICS_ENABLED", "").strip().lower()
    if metrics in ("true", "1", "yes"):
        out["metrics_enabled"] = True
    elif metrics in ("false", "0", "no"):
        out["metrics_enabled"] = False
    out["log_level"] = os.environ.get("DATABASE_CLIENT_LOG_LEVEL") or ""
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
    Generate adapter-compatible client config for database server.

    Writes JSON to settings["output_path"] with:
    - client: enabled, protocol mtls, ssl (cert, key, ca)
    - server_validation: disabled placeholder (adapter contract)
    - auth: placeholder (adapter contract)
    - database_client: base_url, auth/TLS paths, retries, timeouts,
      observability (log_level, metrics_enabled).

    Required keys: output_path, certs_dir (or client_cert_file, client_key_file,
    ca_cert_file), base_url.
    Optional: connect_timeout_seconds, request_timeout_seconds, retry_max_attempts,
    retry_backoff_seconds, log_level, metrics_enabled.
    """
    out_path = settings.get("output_path")
    if out_path is None:
        raise ValueError("output_path is required")
    out_path = Path(out_path)
    certs_dir = Path(settings["certs_dir"])
    base_url = str(settings.get("base_url", "")).strip().rstrip("/")
    if not base_url:
        raise ValueError("base_url is required")

    client_cert = str(
        settings.get("client_cert_file") or certs_dir / "client" / "chunk-writer.crt"
    )
    client_key = str(
        settings.get("client_key_file") or certs_dir / "client" / "chunk-writer.key"
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
        "database_client": {
            "base_url": base_url,
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
        settings["output_path"] = Path("config") / "database_client_config.json"
    generate_client_config(settings)
