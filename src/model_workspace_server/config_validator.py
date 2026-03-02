"""
Validate model workspace server adapter config: schema, required fields,
constraints, file paths, transport and WS + TLS coherence.

Builds on adapter SimpleConfig validator. Returns machine-readable and
user-readable diagnostics with field path and remediation message.
Designed for server startup: on validation errors log diagnostics and stop.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import json
from pathlib import Path
from typing import Any

_ALLOWED_TRANSPORT_TYPES = ("ws",)
_ALLOWED_FALLBACK_POLICIES = ("deny", "allow")
_MIN_PORT = 1
_MAX_PORT = 65535
_MIN_TIMEOUT = 1
_MAX_TIMEOUT = 86400
_MIN_MAX_CONNECTIONS = 1
_MAX_MAX_CONNECTIONS = 100_000


def _err(path: str, message: str, remediation: str = "") -> str:
    """Format a single diagnostic with optional remediation."""
    if remediation:
        return f"{path}: {message} Remediation: {remediation}"
    return f"{path}: {message}"


def _validate_transport(data: dict[str, Any]) -> list[str]:
    """Validate transport section: type, fallback policy, WS + TLS coherence."""
    errors: list[str] = []
    transport = data.get("transport")
    if transport is None:
        errors.append(
            _err("transport", "section is missing", "Add 'transport' object.")
        )
        return errors
    if not isinstance(transport, dict):
        errors.append(
            _err("transport", f"must be an object, got {type(transport).__name__}")
        )
        return errors

    tt = transport.get("transport_type")
    if tt is not None and tt not in _ALLOWED_TRANSPORT_TYPES:
        allowed_tt = ", ".join(repr(x) for x in _ALLOWED_TRANSPORT_TYPES)
        errors.append(
            _err(
                "transport.transport_type",
                f"must be one of {allowed_tt}, got {tt!r}",
                f"Set transport.transport_type to one of {allowed_tt}.",
            )
        )
    policy = transport.get("fallback_policy")
    if policy is not None and policy not in _ALLOWED_FALLBACK_POLICIES:
        allowed = ", ".join(repr(p) for p in _ALLOWED_FALLBACK_POLICIES)
        errors.append(
            _err(
                "transport.fallback_policy",
                f"must be one of {allowed}, got {policy!r}",
                f"Set transport.fallback_policy to one of {allowed}.",
            )
        )
    verify_client = transport.get("verify_client")
    if verify_client is not None and not isinstance(verify_client, bool):
        errors.append(
            _err(
                "transport.verify_client",
                f"must be a boolean, got {type(verify_client).__name__}",
            )
        )

    # WS + TLS coherence: when transport is ws, server cert/key/ca must be present
    if tt == "ws" or (tt is None and data.get("server")):
        server = data.get("server") or {}
        for path_key, path in (
            ("server.server_cert_file", server.get("server_cert_file")),
            ("server.server_key_file", server.get("server_key_file")),
            ("server.server_ca_cert_file", server.get("server_ca_cert_file")),
        ):
            if path and isinstance(path, str) and path.strip():
                p = Path(path)
                if not p.is_file():
                    errors.append(
                        _err(
                            path_key,
                            f"file not found: {path}",
                            "Ensure TLS file exists or fix path in config.",
                        )
                    )
    return errors


def _validate_model_workspace_server_section(data: dict[str, Any]) -> list[str]:
    """Validate model_workspace_server section: runtime_identity, limits, log_dir."""
    errors: list[str] = []
    mws = data.get("model_workspace_server")
    if mws is None:
        errors.append(
            _err(
                "model_workspace_server",
                "section is missing",
                "Add 'model_workspace_server' object (required for model workspace).",
            )
        )
        return errors
    if not isinstance(mws, dict):
        errors.append(
            _err(
                "model_workspace_server",
                f"must be an object, got {type(mws).__name__}",
            )
        )
        return errors

    # runtime_identity
    ri = mws.get("runtime_identity")
    if ri is None:
        errors.append(
            _err(
                "model_workspace_server.runtime_identity",
                "required field is missing",
                "Add runtime_identity with instance_uuid and server_id.",
            )
        )
    elif not isinstance(ri, dict):
        errors.append(
            _err(
                "model_workspace_server.runtime_identity",
                f"must be an object, got {type(ri).__name__}",
            )
        )
    else:
        for key in ("instance_uuid", "server_id"):
            if key not in ri:
                errors.append(
                    _err(
                        f"model_workspace_server.runtime_identity.{key}",
                        "required field is missing",
                        f"Set runtime_identity.{key}.",
                    )
                )
            elif isinstance(ri[key], str) and not ri[key].strip():
                errors.append(
                    _err(
                        f"model_workspace_server.runtime_identity.{key}",
                        "must be non-empty",
                    )
                )

    # limits
    limits = mws.get("limits")
    if limits is None:
        errors.append(
            _err(
                "model_workspace_server.limits",
                "required field is missing",
                "Add limits with max_connections and request_timeout_seconds.",
            )
        )
    elif not isinstance(limits, dict):
        errors.append(
            _err(
                "model_workspace_server.limits",
                f"must be an object, got {type(limits).__name__}",
            )
        )
    else:
        max_conn = limits.get("max_connections")
        if max_conn is not None:
            try:
                n = int(max_conn)
                if n < _MIN_MAX_CONNECTIONS or n > _MAX_MAX_CONNECTIONS:
                    errors.append(
                        _err(
                            "model_workspace_server.limits.max_connections",
                            f"must be between {_MIN_MAX_CONNECTIONS} and "
                            f"{_MAX_MAX_CONNECTIONS}, got {n}",
                        )
                    )
            except (TypeError, ValueError):
                errors.append(
                    _err(
                        "model_workspace_server.limits.max_connections",
                        f"must be an integer, got {type(max_conn).__name__}",
                    )
                )
        timeout = limits.get("request_timeout_seconds")
        if timeout is not None:
            try:
                t = int(timeout)
                if t < _MIN_TIMEOUT or t > _MAX_TIMEOUT:
                    errors.append(
                        _err(
                            "model_workspace_server.limits.request_timeout_seconds",
                            f"must be between {_MIN_TIMEOUT} and {_MAX_TIMEOUT}, "
                            f"got {t}",
                        )
                    )
            except (TypeError, ValueError):
                errors.append(
                    _err(
                        "model_workspace_server.limits.request_timeout_seconds",
                        f"must be an integer, got {type(timeout).__name__}",
                    )
                )

    # log_dir
    log_dir = mws.get("log_dir")
    if log_dir is not None and not isinstance(log_dir, str):
        errors.append(
            _err(
                "model_workspace_server.log_dir",
                f"must be a string, got {type(log_dir).__name__}",
            )
        )
    elif isinstance(log_dir, str) and not log_dir.strip():
        errors.append(
            _err(
                "model_workspace_server.log_dir",
                "must be non-empty when present",
            )
        )

    return errors


def _validate_server_section(data: dict[str, Any]) -> list[str]:
    """Validate server section: log_dir, advertised_host/servername, port bounds."""
    errors: list[str] = []
    server = data.get("server")
    if server is None:
        errors.append(_err("server", "section is missing", "Add 'server' object."))
        return errors
    if not isinstance(server, dict):
        errors.append(_err("server", f"must be an object, got {type(server).__name__}"))
        return errors

    if not (server.get("advertised_host") or server.get("servername")):
        errors.append(
            _err(
                "server",
                "at least one of advertised_host or servername is required",
                "Set server.advertised_host or server.servername.",
            )
        )
    log_dir = server.get("log_dir")
    if log_dir is not None and isinstance(log_dir, str) and not log_dir.strip():
        errors.append(_err("server.log_dir", "must be non-empty when present"))

    port = server.get("server_port") or server.get("port")
    if port is not None:
        try:
            p = int(port)
            if p < _MIN_PORT or p > _MAX_PORT:
                errors.append(
                    _err(
                        "server.server_port",
                        f"must be between {_MIN_PORT} and {_MAX_PORT}, got {p}",
                    )
                )
        except (TypeError, ValueError):
            errors.append(
                _err(
                    "server.server_port",
                    f"must be an integer, got {type(port).__name__}",
                )
            )
    return errors


def validate_config_dict(data: dict[str, Any]) -> list[str]:
    """
    Validate model_workspace_server-specific schema and constraints on config dict.

    Does not run adapter SimpleConfig validation. Use validate_config_file for
    full validation including adapter base.
    """
    errors: list[str] = []
    errors.extend(_validate_server_section(data))
    errors.extend(_validate_transport(data))
    errors.extend(_validate_model_workspace_server_section(data))
    return errors


def validate_config_file(config_path: str | Path) -> list[str]:
    """
    Validate config file: adapter base (SimpleConfig) plus model_workspace_server rules.

    Loads JSON from path, runs adapter validator, then model_workspace_server
    section and transport coherence checks. Returns list of user-readable
    diagnostics with field path and remediation where applicable. Empty list
    means valid. Use on server startup; on non-empty result log diagnostics
    and stop startup.
    """
    path = Path(config_path)
    if not path.is_file():
        return [_err("config_path", f"config file not found: {path}")]

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        return [_err("config_path", f"cannot read config file: {e}")]

    try:
        data = json.loads(raw)
    except ValueError as e:
        return [_err("config", f"invalid JSON: {e}")]

    if not isinstance(data, dict):
        return [_err("config", "root must be a JSON object")]

    errors: list[str] = []

    try:
        from mcp_proxy_adapter.core.config.simple_config import SimpleConfig
    except ImportError:
        errors.append(
            _err(
                "adapter",
                "mcp_proxy_adapter not available; adapter validation skipped",
                "Install mcp-proxy-adapter for full validation.",
            )
        )
    else:
        simple_config = SimpleConfig(str(path))
        simple_config.load()
        adapter_errors = simple_config.validate()
        for err in adapter_errors:
            msg = getattr(err, "message", str(err))
            errors.append(_err("adapter", msg))

    errors.extend(validate_config_dict(data))
    return errors
