"""
Unit tests for database_server config CLI.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from database_server.config_cli import (
    _sample_config_dict,
    _schema_text,
    main,
)


def _valid_db_server_config() -> dict:
    """Minimal valid DB server config for validation tests."""
    return {
        "server": {
            "host": "0.0.0.0",
            "port": 8017,
            "protocol": "mtls",
            "servername": "database-server",
            "advertised_host": "database-server",
            "ssl": {
                "cert": "/certs/server.crt",
                "key": "/certs/server.key",
                "ca": "/certs/ca.crt",
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


def test_sample_config_dict_is_valid_structure() -> None:
    """Sample config dict has required keys and passes as valid structure."""
    sample = _sample_config_dict()
    assert "server" in sample
    assert "transport" in sample
    assert "database_server" in sample
    assert sample["database_server"]["auth"]["require_mtls"] is True
    assert sample["database_server"]["storage"]["backend"] == "local"


def test_schema_text_contains_required_sections() -> None:
    """show-schema output describes server and database_server."""
    text = _schema_text()
    assert "server" in text
    assert "database_server" in text
    assert "required" in text.lower()


def test_cli_show_schema_exit_0() -> None:
    """show-schema subcommand exits 0 and prints schema to stdout."""
    with patch("sys.argv", ["database-server-config-cli", "show-schema"]):
        with patch("sys.stdout", new_callable=StringIO) as out:
            code = main()
    assert code == 0
    assert "database_server" in out.getvalue()


def test_cli_sample_exit_0_and_valid_json() -> None:
    """sample subcommand exits 0 and prints valid JSON to stdout."""
    with patch("sys.argv", ["database-server-config-cli", "sample"]):
        with patch("sys.stdout", new_callable=StringIO) as out:
            code = main()
    assert code == 0
    data = json.loads(out.getvalue())
    assert "server" in data
    assert "database_server" in data


def test_cli_validate_valid_config_exit_0(tmp_path: Path) -> None:
    """validate subcommand exits 0 for valid config (with --no-adapter)."""
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps(_valid_db_server_config(), indent=2), encoding="utf-8")
    with patch("sys.argv", ["db-config-cli", "validate", str(cfg), "--no-adapter"]):
        code = main()
    assert code == 0


def test_cli_validate_invalid_config_exit_1(tmp_path: Path) -> None:
    """validate subcommand exits 1 for invalid config."""
    cfg = tmp_path / "bad.json"
    cfg.write_text("{}", encoding="utf-8")
    with patch("sys.argv", ["db-config-cli", "validate", str(cfg), "--no-adapter"]):
        with patch("sys.stderr", new_callable=StringIO) as err:
            code = main()
    assert code == 1
    assert "database_server" in err.getvalue() or "required" in err.getvalue()


def test_cli_validate_missing_file_exit_1() -> None:
    """validate subcommand exits 1 when config file does not exist."""
    with patch(
        "sys.argv",
        [
            "db-config-cli",
            "validate",
            "/nonexistent/database_server_config.json",
            "--no-adapter",
        ],
    ):
        with patch("sys.stderr", new_callable=StringIO):
            code = main()
    assert code == 1


def test_cli_validate_quiet_exit_1_no_stdout(tmp_path: Path) -> None:
    """validate --quiet with invalid config exits 1 and does not print to stdout."""
    cfg = tmp_path / "bad.json"
    cfg.write_text("{}", encoding="utf-8")
    with patch(
        "sys.argv", ["db-config-cli", "validate", str(cfg), "--no-adapter", "-q"]
    ):
        with patch("sys.stdout", new_callable=StringIO) as out:
            with patch("sys.stderr", new_callable=StringIO):
                code = main()
    assert code == 1
    assert out.getvalue() == ""


def test_cli_generate_succeeds_with_required_args(tmp_path: Path) -> None:
    """generate with -o, certs-dir and mcp-proxy-url creates config file."""
    certs = tmp_path / "certs"
    certs.mkdir()
    (certs / "server").mkdir()
    (certs / "client").mkdir()
    (certs / "ca").mkdir()
    for p in (
        "server/chunk-retriever.crt",
        "server/chunk-retriever.key",
        "client/chunk-retriever.crt",
        "client/chunk-retriever.key",
        "ca/ca.crt",
    ):
        (certs / p).write_text("")
    out_file = tmp_path / "out.json"
    with patch(
        "sys.argv",
        [
            "db-config-cli",
            "generate",
            "-o",
            str(out_file),
            "--certs-dir",
            str(certs),
            "--mcp-proxy-url",
            "https://proxy:3004",
        ],
    ):
        with patch("sys.stderr", new_callable=StringIO):
            code = main()
    assert code == 0
    assert out_file.is_file()


def test_cli_generate_writes_valid_config(tmp_path: Path) -> None:
    """generate writes JSON that validates with --no-adapter."""
    certs = tmp_path / "certs"
    for sub in ("server", "client", "ca"):
        (certs / sub).mkdir(parents=True)
    for name in (
        "server/chunk-retriever.crt",
        "server/chunk-retriever.key",
        "client/chunk-retriever.crt",
        "client/chunk-retriever.key",
        "ca/ca.crt",
    ):
        (certs / name).write_text("")
    out_file = tmp_path / "gen_config.json"
    with patch(
        "sys.argv",
        [
            "db-config-cli",
            "generate",
            "-o",
            str(out_file),
            "--certs-dir",
            str(certs),
            "--mcp-proxy-url",
            "https://proxy:3004",
        ],
    ):
        with patch("sys.stderr", new_callable=StringIO):
            code = main()
    assert code == 0
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert data.get("database_server", {}).get("storage", {}).get("backend") == "local"
