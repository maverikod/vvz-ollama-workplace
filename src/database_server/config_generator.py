"""
Generate DB server config for networked service role.

Builds on adapter config and SimpleConfigGenerator. Produces a single adapter
config with transport, auth, storage settings and mount paths. Supports
prompt-based config creation via merge of template, env, and args.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import json
import os
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from mcp_proxy_adapter.core.config.simple_config_generator import (
    SimpleConfigGenerator,
)


def _resolve_registration_netloc(settings: dict[str, Any]) -> tuple[str, int]:
    """
    Resolve registration host and port: mcp_proxy_url (primary) or
    registration_host + registration_port (fallback). No hardcoded default.
    """
    mcp_proxy_url = str(settings.get("mcp_proxy_url", "")).strip().rstrip("/")
    if mcp_proxy_url:
        parsed = urlparse(mcp_proxy_url)
        if not parsed.scheme or not parsed.hostname:
            raise ValueError("Invalid mcp_proxy_url: scheme and hostname are required")
        host = parsed.hostname
        port = int(parsed.port or (443 if parsed.scheme == "https" else 80))
        return (host, port)
    reg_host = settings.get("registration_host")
    reg_port = settings.get("registration_port")
    if reg_host is not None and reg_port is not None and str(reg_host).strip():
        return (str(reg_host).strip(), int(reg_port))
    raise ValueError(
        "Proxy endpoint required: set mcp_proxy_url or "
        "registration_host and registration_port"
    )


def merge_settings(
    template: dict[str, Any],
    env_overlay: dict[str, Any] | None = None,
    args_overlay: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Merge template with optional env and args overlays (prompt-driven generation).

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


def _default_template(certs_dir: Path) -> dict[str, Any]:
    """
    Default settings template for database server (storage-facing service).

    Proxy endpoint is not set here; use mcp_proxy_url or registration_host/port
    via env (MCP_PROXY_URL, MCP_PROXY_HOST/MCP_PROXY_PORT) or args.
    """
    return {
        "output_path": None,
        "certs_dir": str(certs_dir),
        "server_host": "0.0.0.0",
        "server_port": 8017,
        "server_cert_file": str(certs_dir / "server" / "chunk-retriever.crt"),
        "server_key_file": str(certs_dir / "server" / "chunk-retriever.key"),
        "server_ca_cert_file": str(certs_dir / "ca" / "ca.crt"),
        "registration_protocol": "mtls",
        "registration_cert_file": str(certs_dir / "client" / "chunk-retriever.crt"),
        "registration_key_file": str(certs_dir / "client" / "chunk-retriever.key"),
        "registration_ca_cert_file": str(certs_dir / "ca" / "ca.crt"),
        "registration_server_id": "database-server",
        "registration_server_name": "Database Server",
        "advertised_host": "database-server",
        "log_dir": "/app/logs",
        "data_dir": "/app/data",
        "instance_uuid": None,
        "verify_client": True,
        "storage_backend": "local",
        "max_connections": 100,
        "request_timeout_seconds": 120,
    }


def _env_overlay() -> dict[str, Any]:
    """
    Build overlay from environment. Proxy: MCP_PROXY_URL (primary),
    MCP_PROXY_HOST + MCP_PROXY_PORT (fallback).
    """
    certs_dir = os.environ.get("CERTS_DIR", "")
    out: dict[str, Any] = {}
    if certs_dir:
        p = Path(certs_dir)
        out["certs_dir"] = certs_dir
        out["server_cert_file"] = str(p / "server" / "chunk-retriever.crt")
        out["server_key_file"] = str(p / "server" / "chunk-retriever.key")
        out["server_ca_cert_file"] = str(p / "ca" / "ca.crt")
        out["registration_cert_file"] = str(p / "client" / "chunk-retriever.crt")
        out["registration_key_file"] = str(p / "client" / "chunk-retriever.key")
        out["registration_ca_cert_file"] = str(p / "ca" / "ca.crt")
    out["output_path"] = os.environ.get("DATABASE_SERVER_CONFIG_PATH") or ""
    port = os.environ.get("DATABASE_SERVER_PORT")
    if port:
        try:
            out["server_port"] = int(port)
        except ValueError:
            pass
    out["advertised_host"] = os.environ.get("ADVERTISED_HOST") or ""
    out["log_dir"] = os.environ.get("DATABASE_SERVER_LOG_DIR") or ""
    out["data_dir"] = os.environ.get("DATABASE_SERVER_DATA_DIR") or ""

    mcp_proxy_url = os.environ.get("MCP_PROXY_URL", "").strip().rstrip("/")
    if mcp_proxy_url:
        out["mcp_proxy_url"] = mcp_proxy_url
    else:
        out["registration_host"] = os.environ.get("MCP_PROXY_HOST") or ""
        rport = os.environ.get("MCP_PROXY_PORT")
        if rport:
            try:
                out["registration_port"] = int(rport)
            except ValueError:
                pass

    out["instance_uuid"] = os.environ.get("REGISTRATION_INSTANCE_UUID") or ""
    out["registration_server_id"] = os.environ.get("REGISTRATION_SERVER_ID") or ""
    return out


def generate_server_config(settings: dict[str, Any]) -> None:
    """
    Generate adapter config for database server (networked service role).

    Uses adapter SimpleConfigGenerator for base, then applies server/transport
    and database_server section (transport, auth, storage, mount paths).
    Writes to settings["output_path"].

    Required keys: output_path, certs_dir (or full cert paths), server_port,
    advertised_host, log_dir; proxy endpoint: mcp_proxy_url (primary) or
    registration_host + registration_port (fallback). No hardcoded proxy default.
    Optional: data_dir, verify_client, storage_backend, max_connections,
    request_timeout_seconds.
    """
    out_path = settings.get("output_path")
    if out_path is None:
        raise ValueError("output_path is required")
    out_path = Path(out_path)
    certs_dir = Path(settings["certs_dir"]) if settings.get("certs_dir") else Path(".")
    server_port = int(settings["server_port"])
    advertised_host = str(settings["advertised_host"])
    log_dir = str(settings["log_dir"])
    data_dir = str(settings.get("data_dir", "/app/data"))
    instance_uuid = settings.get("instance_uuid") or str(uuid.uuid4())
    server_id = str(settings.get("registration_server_id") or advertised_host)

    server_cert = str(
        settings.get("server_cert_file") or certs_dir / "server" / "chunk-retriever.crt"
    )
    server_key = str(
        settings.get("server_key_file") or certs_dir / "server" / "chunk-retriever.key"
    )
    ca_crt = str(settings.get("server_ca_cert_file") or certs_dir / "ca" / "ca.crt")
    client_cert = str(
        settings.get("registration_cert_file")
        or certs_dir / "client" / "chunk-retriever.crt"
    )
    client_key = str(
        settings.get("registration_key_file")
        or certs_dir / "client" / "chunk-retriever.key"
    )
    reg_ca = str(
        settings.get("registration_ca_cert_file") or certs_dir / "ca" / "ca.crt"
    )
    reg_host, reg_port = _resolve_registration_netloc(settings)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    generator = SimpleConfigGenerator()
    generator.generate(
        protocol="mtls",
        with_proxy=True,
        out_path=str(out_path),
        server_host=str(settings.get("server_host", "0.0.0.0")),
        server_port=server_port,
        server_cert_file=server_cert,
        server_key_file=server_key,
        server_ca_cert_file=ca_crt,
        registration_host=reg_host,
        registration_port=reg_port,
        registration_protocol="mtls",
        registration_cert_file=client_cert,
        registration_key_file=client_key,
        registration_ca_cert_file=reg_ca,
        registration_server_id=server_id,
        registration_server_name=str(
            settings.get("registration_server_name", "Database Server")
        ),
        instance_uuid=instance_uuid,
    )

    data = json.loads(out_path.read_text(encoding="utf-8"))
    data.setdefault("server", {})
    data["server"]["servername"] = advertised_host
    data["server"]["advertised_host"] = advertised_host
    data["server"]["log_dir"] = log_dir
    data.setdefault("registration", {})
    data["registration"]["server_id"] = server_id
    data["transport"] = {
        "verify_client": bool(settings.get("verify_client", True)),
    }
    data["database_server"] = {
        "auth": {
            "require_mtls": True,
        },
        "storage": {
            "backend": str(settings.get("storage_backend", "local")),
            "data_dir": data_dir,
        },
        "mount_paths": {
            "data_dir": data_dir,
            "log_dir": log_dir,
            "certs_dir": str(settings.get("certs_dir") or certs_dir),
        },
        "limits": {
            "max_connections": int(settings.get("max_connections", 100)),
            "request_timeout_seconds": int(
                settings.get("request_timeout_seconds", 120)
            ),
        },
        "runtime_identity": {
            "instance_uuid": instance_uuid,
            "server_id": server_id,
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
    Generate config from merged template, env overlay, and args overlay.

    If template is None, uses default template with certs_dir from env or cwd.
    """
    certs_dir = Path(
        (args_overlay or {}).get("certs_dir")
        or (env_overlay or {}).get("certs_dir")
        or os.environ.get("CERTS_DIR", "mtls_certificates")
    )
    tpl = template or _default_template(certs_dir)
    env = env_overlay if env_overlay is not None else _env_overlay()
    args = args_overlay or {}
    settings = merge_settings(tpl, env, args)
    if not settings.get("output_path"):
        settings["output_path"] = Path("config") / "database_server_config.json"
    generate_server_config(settings)
