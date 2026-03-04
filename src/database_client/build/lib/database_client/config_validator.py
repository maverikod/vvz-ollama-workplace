"""
Validate DB client config and transport/auth/security consistency.

Builds on adapter config and adapter base validator (SimpleConfig). Detects
incompatible settings versus DB server contract (mTLS). Validator runs on
client init/start; on validation errors returns error and raises exception.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    from mcp_proxy_adapter.core.config.simple_config import SimpleConfig
except ImportError:
    SimpleConfig = None


class DatabaseClientConfigError(Exception):
    """
    Raised when DB client config validation fails.

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


def _valid_base_url(value: Any) -> tuple[bool, str]:
    """Check base_url is non-empty and valid https URL. Returns (ok, message)."""
    if value is None:
        return (False, "base_url is required")
    s = str(value).strip().rstrip("/")
    if not s:
        return (False, "base_url must be non-empty")
    try:
        parsed = urlparse(s if "://" in s else "https://" + s)
    except Exception as e:
        return (False, f"base_url invalid URL: {e}")
    scheme = (parsed.scheme or "https").lower()
    if scheme not in ("http", "https"):
        return (False, "base_url must use http:// or https:// scheme")
    if not parsed.hostname:
        return (False, "base_url must have a host")
    if scheme != "https":
        return (False, "base_url must use https:// for DB server contract (mTLS)")
    return (True, "")


def _file_path_exists(path: Any) -> bool:
    """Return True if path is a non-empty string and file exists."""
    if not path or not isinstance(path, str):
        return False
    return Path(path).expanduser().is_file()


def _validate_database_client_section(dbc: Any, errors: list[tuple[str, str]]) -> None:
    """Append validation errors for database_client section."""
    prefix = "database_client"
    if not isinstance(dbc, dict):
        errors.append((prefix, "must be an object"))
        return

    ok, msg = _valid_base_url(dbc.get("base_url"))
    if not ok:
        errors.append((f"{prefix}.base_url", msg))

    base_url = str(dbc.get("base_url", "")).strip().lower()
    use_tls = "https://" in base_url or (
        base_url and not base_url.startswith("http://")
    )

    for key in ("client_cert_file", "client_key_file", "ca_cert_file"):
        val = dbc.get(key)
        if not val or not isinstance(val, str) or not str(val).strip():
            if use_tls:
                errors.append(
                    (f"{prefix}.{key}", "required when base_url is https (mTLS)")
                )
        elif use_tls and not _file_path_exists(val):
            errors.append((f"{prefix}.{key}", f"file not found: {val}"))

    for key, min_val in (
        ("connect_timeout_seconds", 1),
        ("request_timeout_seconds", 1),
    ):
        val = dbc.get(key)
        if val is not None:
            try:
                n = int(val)
                if n < min_val:
                    errors.append((f"{prefix}.{key}", f"must be >= {min_val}, got {n}"))
            except (TypeError, ValueError):
                errors.append((f"{prefix}.{key}", "must be a positive integer"))

    retry_max = dbc.get("retry_max_attempts")
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

    retry_backoff = dbc.get("retry_backoff_seconds")
    if retry_backoff is not None:
        try:
            x = float(retry_backoff)
            if x < 0:
                errors.append(
                    (f"{prefix}.retry_backoff_seconds", f"must be >= 0, got {x}")
                )
        except (TypeError, ValueError):
            errors.append(
                (
                    f"{prefix}.retry_backoff_seconds",
                    "must be a non-negative number",
                )
            )

    obs = dbc.get("observability")
    if obs is not None and not isinstance(obs, dict):
        errors.append((f"{prefix}.observability", "must be an object"))


def _validate_client_section(client: Any, errors: list[tuple[str, str]]) -> None:
    """Append validation errors for client section (TLS coherence with adapter)."""
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
    Ensures database_client and client sections are consistent with DB server
    contract (mTLS). Returns list of (field_path, message); empty if valid.
    """
    errors: list[tuple[str, str]] = []

    dbc = app_config.get("database_client")
    if dbc is None:
        errors.append(("database_client", "section is required"))
    else:
        _validate_database_client_section(dbc, errors)

    client = app_config.get("client")
    _validate_client_section(client, errors)

    # Incompatible: https base_url but client TLS not properly set
    dbc = app_config.get("database_client")
    if isinstance(dbc, dict):
        base_url = str(dbc.get("base_url", "")).strip().lower()
        if "https://" in base_url or (base_url and not base_url.startswith("http://")):
            client = app_config.get("client") or {}
            if (
                not client.get("enabled")
                or str(client.get("protocol", "")).lower() != "mtls"
            ):
                errors.append(
                    (
                        "client",
                        "client.enabled=true and client.protocol=mtls required "
                        "for https base_url (DB server contract)",
                    )
                )

    return errors


def validate_config(config_path: str | Path) -> None:
    """
    Load config file, run adapter base validation then DB client validation.

    Validator runs on client init/start. On validation errors: raises
    DatabaseClientConfigError with deterministic error list (field path and
    message). Caller must not proceed with connection.
    """
    path = Path(config_path)
    if not path.is_file():
        raise DatabaseClientConfigError(
            [("config_path", f"config file not found: {path}")]
        )

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        raise DatabaseClientConfigError(
            [("config_path", f"cannot read config file: {e}")]
        ) from e

    try:
        app_config = json.loads(raw)
    except json.JSONDecodeError as e:
        raise DatabaseClientConfigError([("config", f"invalid JSON: {e}")]) from e

    if not isinstance(app_config, dict):
        raise DatabaseClientConfigError([("config", "root must be a JSON object")])

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
        raise DatabaseClientConfigError(errors)
