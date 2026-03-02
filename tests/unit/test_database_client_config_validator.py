"""
Unit tests for database_client config validator.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import json
from pathlib import Path

import pytest

from database_client.config_validator import (
    DatabaseClientConfigError,
    validate_config,
    validate_config_dict,
)


def _make_certs_dir(tmp_path: Path) -> Path:
    """Create minimal cert dir structure with placeholder files."""
    certs = tmp_path / "certs"
    for sub in ("client", "ca"):
        (certs / sub).mkdir(parents=True)
    for name in (
        "client/chunk-writer.crt",
        "client/chunk-writer.key",
        "ca/ca.crt",
    ):
        (certs / name).write_text("")
    return certs


def _valid_db_client_config(certs: Path) -> dict:
    """Minimal valid database client adapter config (database_client + client mTLS)."""
    return {
        "client": {
            "enabled": True,
            "protocol": "mtls",
            "ssl": {
                "cert": str(certs / "client" / "chunk-writer.crt"),
                "key": str(certs / "client" / "chunk-writer.key"),
                "ca": str(certs / "ca" / "ca.crt"),
            },
        },
        "server_validation": {"enabled": False},
        "auth": {"use_token": False},
        "database_client": {
            "base_url": "https://database-server:8017",
            "client_cert_file": str(certs / "client" / "chunk-writer.crt"),
            "client_key_file": str(certs / "client" / "chunk-writer.key"),
            "ca_cert_file": str(certs / "ca" / "ca.crt"),
            "connect_timeout_seconds": 30,
            "request_timeout_seconds": 120,
            "retry_max_attempts": 3,
            "retry_backoff_seconds": 2.0,
            "observability": {"log_level": "INFO", "metrics_enabled": False},
        },
    }


def test_validate_config_dict_missing_database_client() -> None:
    """Missing database_client section yields error."""
    errors = validate_config_dict({})
    assert any("database_client" in path for path, _ in errors)
    assert any("required" in msg for _, msg in errors)


def test_validate_config_dict_valid_minimal(tmp_path: Path) -> None:
    """Valid minimal database_client (https + certs) returns no errors."""
    certs = _make_certs_dir(tmp_path)
    config = _valid_db_client_config(certs)
    errors = validate_config_dict(config)
    assert errors == []


def test_validate_config_dict_https_requires_certs() -> None:
    """https base_url without cert paths yields errors."""
    config = {
        "database_client": {
            "base_url": "https://database-server:8017",
        },
        "client": {"enabled": False},
    }
    errors = validate_config_dict(config)
    assert any(
        "client_cert_file" in path or "ca_cert_file" in path or "required" in msg
        for path, msg in errors
    )


def test_validate_config_dict_http_base_url_rejected() -> None:
    """http:// base_url yields error (DB server contract requires https/mTLS)."""
    config = {
        "database_client": {
            "base_url": "http://database-server:8017",
        },
    }
    errors = validate_config_dict(config)
    assert any("https" in msg for _, msg in errors)


def test_validate_config_dict_empty_base_url() -> None:
    """Empty base_url yields error."""
    config = {
        "database_client": {"base_url": ""},
    }
    errors = validate_config_dict(config)
    assert any("base_url" in path for path, _ in errors)


def test_validate_config_dict_negative_timeout() -> None:
    """Zero connect_timeout_seconds yields error."""
    config = {
        "database_client": {
            "base_url": "https://database-server:8017",
            "connect_timeout_seconds": 0,
        },
    }
    errors = validate_config_dict(config)
    assert any("connect_timeout" in path for path, _ in errors)


def test_validate_config_dict_negative_retry_backoff() -> None:
    """Negative retry_backoff_seconds yields error."""
    config = {
        "database_client": {
            "base_url": "https://database-server:8017",
            "retry_backoff_seconds": -1,
        },
    }
    errors = validate_config_dict(config)
    assert any("retry_backoff" in path for path, _ in errors)


def test_validate_config_dict_https_requires_client_mtls(tmp_path: Path) -> None:
    """https base_url without client.enabled mtls yields error."""
    certs = _make_certs_dir(tmp_path)
    config = _valid_db_client_config(certs)
    config["client"]["enabled"] = False
    errors = validate_config_dict(config)
    assert any(
        "client.enabled" in msg or "client.protocol=mtls" in msg for _, msg in errors
    )


def test_validate_config_dict_client_mtls_missing_ssl() -> None:
    """client enabled mtls without ssl section yields errors."""
    config = {
        "database_client": {"base_url": "https://database-server:8017"},
        "client": {"enabled": True, "protocol": "mtls"},
    }
    errors = validate_config_dict(config)
    assert any("client" in path and "ssl" in path for path, _ in errors)


def test_validate_config_file_not_found() -> None:
    """validate_config raises on missing file."""
    with pytest.raises(DatabaseClientConfigError) as exc_info:
        validate_config(Path("/nonexistent/database_client_config.json"))
    assert exc_info.value.errors[0][0] == "config_path"
    assert "not found" in exc_info.value.errors[0][1]


def test_validate_config_invalid_json(tmp_path: Path) -> None:
    """validate_config raises on invalid JSON."""
    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    with pytest.raises(DatabaseClientConfigError) as exc_info:
        validate_config(bad)
    assert any("JSON" in msg for _, msg in exc_info.value.errors)


def test_validate_config_valid_file(tmp_path: Path) -> None:
    """Generated client config passes validate_config_dict (client-specific rules)."""
    from database_client.config_generator import generate_client_config

    certs = _make_certs_dir(tmp_path)
    out_file = tmp_path / "database_client_config.json"
    generate_client_config(
        {
            "output_path": out_file,
            "certs_dir": str(certs),
            "base_url": "https://database-server:8017",
        }
    )
    app_config = json.loads(out_file.read_text(encoding="utf-8"))
    errors = validate_config_dict(app_config)
    assert errors == [], f"Generated config should pass client validation: {errors}"


def test_validate_config_missing_section_raises(tmp_path: Path) -> None:
    """validate_config raises when database_client missing."""
    config = {"client": {"enabled": False}}
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(DatabaseClientConfigError) as exc_info:
        validate_config(path)
    assert any("database_client" in p for p, _ in exc_info.value.errors)


def test_error_messages() -> None:
    """DatabaseClientConfigError.messages() returns list of strings."""
    err = DatabaseClientConfigError([("a.b", "msg1"), ("c", "msg2")])
    assert err.errors == [("a.b", "msg1"), ("c", "msg2")]
    assert "a.b" in err.messages()[0]
    assert "msg1" in err.messages()[0]
