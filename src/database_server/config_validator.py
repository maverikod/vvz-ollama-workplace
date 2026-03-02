"""
Validate database server adapter config: endpoints, auth/TLS, persistence, limits.

Builds on adapter SimpleConfig validation; adds database_server section and
client-contract compatibility. For server startup: run validator and on
errors log diagnostics and stop startup.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any

VALID_STORAGE_BACKENDS: frozenset[str] = frozenset({"local"})


def validate_database_server_config(app_config: dict[str, Any]) -> list[str]:
    """
    Validate database-server-specific config (database_server, transport, server TLS).

    Returns list of error messages with field path; empty if valid.
    Does not run adapter base validation (use validate_config for full check).
    """
    errors: list[str] = []

    # Server: mTLS coherence
    server_cfg = app_config.get("server") or {}
    if not isinstance(server_cfg, dict):
        errors.append("server must be an object")
        return errors

    proto = str(server_cfg.get("protocol", "http")).lower()
    if proto == "mtls":
        ssl_cfg = server_cfg.get("ssl") or {}
        if not isinstance(ssl_cfg, dict):
            errors.append("server.ssl must be an object when protocol is mtls")
        else:
            if not (ssl_cfg.get("cert") and ssl_cfg.get("key")):
                errors.append(
                    "server.ssl.cert and server.ssl.key are required when "
                    "server.protocol is mtls"
                )
            if server_cfg.get("ssl", {}).get("ca"):
                ca = server_cfg["ssl"]["ca"]
                if not isinstance(ca, str) or not ca.strip():
                    errors.append("server.ssl.ca must be a non-empty path when set")

        transport = app_config.get("transport") or {}
        if not isinstance(transport, dict):
            errors.append("transport must be an object")
        elif not transport.get("verify_client"):
            errors.append(
                "transport.verify_client must be true when server.protocol is mtls"
            )

    # Required server fields for client contract (base_url = host:port, identity)
    port = server_cfg.get("port")
    if port is not None:
        try:
            p = int(port)
            if p <= 0 or p > 65535:
                errors.append("server.port must be between 1 and 65535")
        except (TypeError, ValueError):
            errors.append("server.port must be an integer")

    advertised = server_cfg.get("advertised_host") or server_cfg.get("servername")
    if not advertised or not isinstance(advertised, str) or not str(advertised).strip():
        errors.append(
            "server.advertised_host or server.servername is required "
            "(client contract: advertised identity)"
        )

    log_dir = server_cfg.get("log_dir")
    if log_dir is not None and (not isinstance(log_dir, str) or not log_dir.strip()):
        errors.append("server.log_dir must be a non-empty string when set")

    # database_server section (mandatory for DB server role)
    db = app_config.get("database_server")
    if db is None:
        errors.append("database_server section is required")
        return errors
    if not isinstance(db, dict):
        errors.append("database_server must be an object")
        return errors

    # database_server.auth
    auth = db.get("auth")
    if auth is not None:
        if not isinstance(auth, dict):
            errors.append("database_server.auth must be an object")
        elif auth.get("require_mtls") is not True:
            errors.append("database_server.auth.require_mtls must be true")

    # database_server.storage
    storage = db.get("storage")
    if storage is None:
        errors.append("database_server.storage is required")
    elif not isinstance(storage, dict):
        errors.append("database_server.storage must be an object")
    else:
        backend = storage.get("backend")
        if backend is not None:
            if not isinstance(backend, str) or backend not in VALID_STORAGE_BACKENDS:
                errors.append(
                    "database_server.storage.backend must be one of %s"
                    % sorted(VALID_STORAGE_BACKENDS)
                )
        data_dir = storage.get("data_dir")
        if data_dir is not None and (
            not isinstance(data_dir, str) or not data_dir.strip()
        ):
            errors.append("database_server.storage.data_dir must be non-empty string")

    # database_server.mount_paths (optional but if present must be consistent)
    mount_paths = db.get("mount_paths")
    if mount_paths is not None:
        if not isinstance(mount_paths, dict):
            errors.append("database_server.mount_paths must be an object")
        else:
            for key in ("data_dir", "log_dir", "certs_dir"):
                v = mount_paths.get(key)
                if v is not None and (not isinstance(v, str) or not str(v).strip()):
                    errors.append(
                        "database_server.mount_paths.%s must be non-empty string" % key
                    )

    # database_server.limits
    limits = db.get("limits")
    if limits is not None:
        if not isinstance(limits, dict):
            errors.append("database_server.limits must be an object")
        else:
            max_conn = limits.get("max_connections")
            if max_conn is not None:
                try:
                    n = int(max_conn)
                    if n < 1:
                        errors.append(
                            "database_server.limits.max_connections must be >= 1"
                        )
                except (TypeError, ValueError):
                    errors.append(
                        "database_server.limits.max_connections must be an integer"
                    )
            timeout = limits.get("request_timeout_seconds")
            if timeout is not None:
                try:
                    t = int(timeout)
                    if t < 1:
                        errors.append(
                            "database_server.limits.request_timeout_seconds "
                            "must be >= 1"
                        )
                except (TypeError, ValueError):
                    errors.append(
                        "database_server.limits.request_timeout_seconds must be "
                        "an integer"
                    )

    # database_server.runtime_identity (optional; instance_uuid and server_id)
    runtime = db.get("runtime_identity")
    if runtime is not None:
        if not isinstance(runtime, dict):
            errors.append("database_server.runtime_identity must be an object")
        else:
            for key in ("instance_uuid", "server_id"):
                v = runtime.get(key)
                if v is not None and (not isinstance(v, str) or not str(v).strip()):
                    errors.append(
                        "database_server.runtime_identity.%s must be non-empty string"
                        % key
                    )

    return errors


def validate_config(
    config_path: str | Path,
    *,
    skip_adapter: bool = False,
) -> list[str]:
    """
    Load config file; run adapter validation (unless skipped), then DB-server.

    Returns combined list of error messages; empty if valid.
    """
    path = Path(config_path)
    if not path.is_file():
        return ["Config file not found: %s" % path]

    try:
        app_config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return ["Invalid JSON: %s" % e]

    errors: list[str] = []

    if not skip_adapter:
        try:
            from mcp_proxy_adapter.core.config.simple_config import SimpleConfig
        except ImportError:
            pass
        else:
            simple_config = SimpleConfig(str(path))
            simple_config.load()
            adapter_errors = simple_config.validate()
            for err in adapter_errors:
                errors.append(getattr(err, "message", str(err)))

    errors.extend(validate_database_server_config(app_config))
    return errors


def validate_config_or_exit(
    config_path: str | Path,
    logger: logging.Logger,
    *,
    skip_adapter: bool = False,
) -> None:
    """
    Validate config; on any error log each message and exit with code 1.

    Use on server startup so invalid config blocks startup with explicit diagnostics.
    """
    errors = validate_config(config_path, skip_adapter=skip_adapter)
    if not errors:
        return
    for msg in errors:
        logger.error("Validation: %s", msg)
    sys.exit(1)
