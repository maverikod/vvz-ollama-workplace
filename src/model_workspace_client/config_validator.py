"""
Validate model workspace client adapter config before runtime connection.

Runs adapter base validation (SimpleConfig) then client-specific checks:
endpoint URL, WS options, TLS cert paths, retry policy. Detects invalid
combinations (e.g. wss without certs). On errors returns diagnostics and
raises ModelWorkspaceClientConfigError for client init/start.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import json
from pathlib import Path
from urllib.parse import urlparse
from typing import Any

# Adapter base validation (optional dependency).
try:
    from mcp_proxy_adapter.core.config.simple_config import SimpleConfig
except ImportError:
    SimpleConfig = None


class ModelWorkspaceClientConfigError(Exception):
    """
    Raised when client config validation fails.

    Attributes:
        errors: List of (field_path, message) for deterministic classification.
    """

    def __init__(self, errors: list[tuple[str, str]]) -> None:
        self.errors = list(errors)
        msg = "; ".join(f"{path}: {m}" for path, m in self.errors)
        super().__init__(msg)

    def messages(self) -> list[str]:
        """Return user-readable error messages."""
        return [f"{path}: {m}" for path, m in self.errors]


def _valid_ws_endpoint(value: Any) -> tuple[bool, str]:
    """Check ws_endpoint is non-empty and valid ws/wss URL. Returns (ok, message)."""
    if value is None:
        return (False, "ws_endpoint is required")
    s = str(value).strip()
    if not s:
        return (False, "ws_endpoint must be non-empty")
    try:
        parsed = urlparse(s)
    except Exception as e:
        return (False, f"ws_endpoint invalid URL: {e}")
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("ws", "wss"):
        return (False, "ws_endpoint must use ws:// or wss:// scheme")
    if not parsed.hostname:
        return (False, "ws_endpoint must have a host")
    return (True, "")


def _file_path_exists(path: Any) -> bool:
    """Return True if path is a non-empty string and file exists."""
    if not path or not isinstance(path, str):
        return False
    return Path(path).expanduser().is_file()


def _validate_model_workspace_client_section(
    mwc: Any, errors: list[tuple[str, str]]
) -> None:
    """Append validation errors for model_workspace_client section."""
    prefix = "model_workspace_client"
    if not isinstance(mwc, dict):
        errors.append((prefix, "must be an object"))
        return

    ok, msg = _valid_ws_endpoint(mwc.get("ws_endpoint"))
    if not ok:
        errors.append((f"{prefix}.ws_endpoint", msg))

    ws_endpoint = str(mwc.get("ws_endpoint", "")).strip().lower()
    use_tls = ws_endpoint.startswith("wss://")

    for key in ("client_cert_file", "client_key_file", "ca_cert_file"):
        val = mwc.get(key)
        if not val or not isinstance(val, str) or not str(val).strip():
            if use_tls:
                errors.append(
                    (f"{prefix}.{key}", "required when ws_endpoint is wss://")
                )
        elif use_tls and not _file_path_exists(val):
            errors.append((f"{prefix}.{key}", f"file not found: {val}"))

    for key, min_val in (
        ("connect_timeout_seconds", 1),
        ("request_timeout_seconds", 1),
    ):
        val = mwc.get(key)
        if val is not None:
            try:
                n = int(val)
                if n < min_val:
                    errors.append((f"{prefix}.{key}", f"must be >= {min_val}, got {n}"))
            except (TypeError, ValueError):
                errors.append((f"{prefix}.{key}", "must be a positive integer"))

    retry_max = mwc.get("retry_max_attempts")
    if retry_max is not None:
        try:
            n = int(retry_max)
            if n < 0:
                errors.append(
                    (f"{prefix}.retry_max_attempts", f"must be >= 0, got {n}")
                )
        except (TypeError, ValueError):
            errors.append(
                (f"{prefix}.retry_max_attempts", "must be a non-negative integer")
            )

    retry_backoff = mwc.get("retry_backoff_seconds")
    if retry_backoff is not None:
        try:
            x = float(retry_backoff)
            if x < 0:
                errors.append(
                    (f"{prefix}.retry_backoff_seconds", f"must be >= 0, got {x}")
                )
        except (TypeError, ValueError):
            errors.append(
                (f"{prefix}.retry_backoff_seconds", "must be a non-negative number")
            )

    obs = mwc.get("observability")
    if obs is not None and not isinstance(obs, dict):
        errors.append((f"{prefix}.observability", "must be an object"))


def _validate_client_section(client: Any, errors: list[tuple[str, str]]) -> None:
    """Append validation errors for client section (TLS coherence)."""
    prefix = "client"
    if not isinstance(client, dict):
        return
    if not client.get("enabled"):
        return
    proto = str(client.get("protocol", "")).lower()
    if proto != "mtls":
        return
    ssl = client.get("ssl")
    if not isinstance(ssl, dict):
        errors.append((f"{prefix}.ssl", "required when client is enabled with mtls"))
        return
    for key in ("cert", "key", "ca"):
        val = ssl.get(key)
        if not val or not isinstance(val, str) or not str(val).strip():
            errors.append((f"{prefix}.ssl.{key}", "required for mtls"))
        elif not _file_path_exists(val):
            errors.append((f"{prefix}.ssl.{key}", f"file not found: {val}"))


def validate_config_dict(app_config: dict[str, Any]) -> list[tuple[str, str]]:
    """
    Validate client-specific sections of adapter config dict.

    Does not run adapter base validation (use validate_config for full check).
    Returns list of (field_path, message); empty if valid.
    """
    errors: list[tuple[str, str]] = []

    mwc = app_config.get("model_workspace_client")
    if mwc is None:
        errors.append(("model_workspace_client", "section is required"))
    else:
        _validate_model_workspace_client_section(mwc, errors)

    client = app_config.get("client")
    _validate_client_section(client, errors)

    # Invalid combination: wss endpoint but client TLS not properly set
    mwc = app_config.get("model_workspace_client")
    if isinstance(mwc, dict):
        ws_endpoint = str(mwc.get("ws_endpoint", "")).strip().lower()
        if ws_endpoint.startswith("wss://"):
            client = app_config.get("client") or {}
            if (
                not client.get("enabled")
                or str(client.get("protocol", "")).lower() != "mtls"
            ):
                errors.append(
                    (
                        "client",
                        "wss:// requires client.enabled=true and client.protocol=mtls",
                    )
                )

    return errors


def validate_config(config_path: str | Path) -> None:
    """
    Load config file, run adapter base validation then client-specific validation.

    Validator runs on client init/start. On validation errors: raises
    ModelWorkspaceClientConfigError with deterministic error list (field path
    and message). Caller should not proceed with connection.
    """
    path = Path(config_path)
    if not path.is_file():
        raise ModelWorkspaceClientConfigError(
            [("config_path", f"config file not found: {path}")]
        )

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        raise ModelWorkspaceClientConfigError(
            [("config_path", f"cannot read config file: {e}")]
        ) from e

    try:
        app_config = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ModelWorkspaceClientConfigError([("config", f"invalid JSON: {e}")]) from e

    if not isinstance(app_config, dict):
        raise ModelWorkspaceClientConfigError(
            [("config", "root must be a JSON object")]
        )

    errors: list[tuple[str, str]] = []

    if SimpleConfig is not None:
        try:
            simple_config = SimpleConfig(str(path))
            simple_config.load()
            adapter_errors = simple_config.validate()
            for err in adapter_errors:
                msg = getattr(err, "message", str(err))
                errors.append(("adapter", msg))
        except Exception as e:
            errors.append(("adapter", f"adapter validation failed: {e}"))

    client_errors = validate_config_dict(app_config)
    errors.extend(client_errors)

    if errors:
        raise ModelWorkspaceClientConfigError(errors)
