"""
Unit tests for database_server config validator.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import json
import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from database_server.config_validator import (  # noqa: E402
    validate_config,
    validate_config_or_exit,
    validate_database_server_config,
)


def _valid_db_server_config() -> dict:
    """Minimal valid DB server adapter config (database_server + server + transport)."""
    return {
        "server": {
            "host": "0.0.0.0",
            "port": 8017,
            "protocol": "mtls",
            "servername": "database-server",
            "advertised_host": "database-server",
            "ssl": {
                "cert": "/certs/server/chunk-retriever.crt",
                "key": "/certs/server/chunk-retriever.key",
                "ca": "/certs/ca/ca.crt",
            },
            "log_dir": "/app/logs",
        },
        "transport": {"verify_client": True},
        "database_server": {
            "auth": {"require_mtls": True},
            "storage": {"backend": "local", "data_dir": "/app/data"},
            "mount_paths": {
                "data_dir": "/app/data",
                "log_dir": "/app/logs",
                "certs_dir": "/certs",
            },
            "limits": {
                "max_connections": 100,
                "request_timeout_seconds": 120,
            },
            "runtime_identity": {
                "instance_uuid": "test-uuid",
                "server_id": "database-server",
            },
        },
    }


def test_validate_database_server_config_valid() -> None:
    """Valid full database server config yields no errors."""
    assert validate_database_server_config(_valid_db_server_config()) == []


def test_validate_database_server_config_missing_database_server_section() -> None:
    """Missing database_server section yields error."""
    config = {"server": {"port": 8017, "advertised_host": "x"}}
    errors = validate_database_server_config(config)
    assert len(errors) >= 1
    assert any("database_server" in e for e in errors)


def test_validate_database_server_config_database_server_not_object() -> None:
    """database_server must be an object."""
    config = {"server": {"port": 8017, "advertised_host": "x"}, "database_server": []}
    errors = validate_database_server_config(config)
    assert any("database_server must be an object" in e for e in errors)


def test_validate_database_server_config_mtls_requires_ssl_cert_key() -> None:
    """When server.protocol is mtls, server.ssl.cert and server.ssl.key are required."""
    config = _valid_db_server_config()
    config["server"]["ssl"] = {}
    errors = validate_database_server_config(config)
    assert any("server.ssl" in e and "cert" in e for e in errors)


def test_validate_database_server_config_mtls_requires_verify_client() -> None:
    """When server.protocol is mtls, transport.verify_client must be true."""
    config = _valid_db_server_config()
    config["transport"]["verify_client"] = False
    errors = validate_database_server_config(config)
    assert any("verify_client" in e for e in errors)


def test_validate_database_server_config_require_mtls_must_be_true() -> None:
    """database_server.auth.require_mtls must be true."""
    config = _valid_db_server_config()
    config["database_server"]["auth"]["require_mtls"] = False
    errors = validate_database_server_config(config)
    assert any("require_mtls" in e for e in errors)


def test_validate_database_server_config_storage_required() -> None:
    """database_server.storage is required."""
    config = _valid_db_server_config()
    del config["database_server"]["storage"]
    errors = validate_database_server_config(config)
    assert any("database_server.storage" in e for e in errors)


def test_validate_database_server_config_storage_backend_invalid() -> None:
    """database_server.storage.backend must be one of allowed values."""
    config = _valid_db_server_config()
    config["database_server"]["storage"]["backend"] = "redis"
    errors = validate_database_server_config(config)
    assert any("storage.backend" in e or "backend" in e for e in errors)


def test_validate_database_server_config_limits_max_connections_invalid() -> None:
    """database_server.limits.max_connections must be >= 1 integer."""
    config = _valid_db_server_config()
    config["database_server"]["limits"]["max_connections"] = 0
    errors = validate_database_server_config(config)
    assert any("max_connections" in e for e in errors)


def test_validate_database_server_config_advertised_host_required() -> None:
    """server.advertised_host or server.servername is required."""
    config = _valid_db_server_config()
    config["server"]["advertised_host"] = ""
    config["server"]["servername"] = ""
    errors = validate_database_server_config(config)
    assert any("advertised_host" in e or "servername" in e for e in errors)


def test_validate_database_server_config_server_port_invalid() -> None:
    """server.port must be 1-65535."""
    config = _valid_db_server_config()
    config["server"]["port"] = 0
    errors = validate_database_server_config(config)
    assert any("server.port" in e for e in errors)


def test_validate_config_file_not_found(tmp_path: Path) -> None:
    """validate_config returns error when file does not exist."""
    errors = validate_config(tmp_path / "nonexistent.json", skip_adapter=True)
    assert len(errors) == 1
    assert "not found" in errors[0] or "nonexistent" in errors[0]


def test_validate_config_invalid_json(tmp_path: Path) -> None:
    """validate_config returns error for invalid JSON."""
    bad = tmp_path / "bad.json"
    bad.write_text("{ invalid }", encoding="utf-8")
    errors = validate_config(bad, skip_adapter=True)
    assert len(errors) >= 1
    assert "JSON" in errors[0]


def test_validate_config_valid_file_skip_adapter(tmp_path: Path) -> None:
    """validate_config with skip_adapter=True validates only DB-server section."""
    cfg = tmp_path / "db_config.json"
    cfg.write_text(
        json.dumps(_valid_db_server_config(), indent=2),
        encoding="utf-8",
    )
    errors = validate_config(cfg, skip_adapter=True)
    assert errors == []


def test_validate_config_or_exit_exits_on_errors(tmp_path: Path) -> None:
    """validate_config_or_exit calls sys.exit(1) when validation fails."""
    bad = tmp_path / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    logger = logging.getLogger("test_db_validator")
    with pytest.raises(SystemExit) as exc_info:
        validate_config_or_exit(bad, logger, skip_adapter=True)
    assert exc_info.value.code == 1


def test_validate_config_or_exit_does_not_exit_when_valid(tmp_path: Path) -> None:
    """validate_config_or_exit does not exit when config is valid."""
    cfg = tmp_path / "db_config.json"
    cfg.write_text(
        json.dumps(_valid_db_server_config(), indent=2),
        encoding="utf-8",
    )
    logger = logging.getLogger("test_db_validator")
    validate_config_or_exit(cfg, logger, skip_adapter=True)
    # No exception = success
