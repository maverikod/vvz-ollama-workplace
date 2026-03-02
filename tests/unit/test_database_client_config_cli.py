"""
Unit tests for database_client config_cli (generate, validate, show-schema,
test-connection).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    """Run database-client-config-cli via python -m."""
    return subprocess.run(
        [sys.executable, "-m", "database_client.config_cli"] + list(args),
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )


def _make_certs_dir(tmp_path: Path) -> Path:
    """Create minimal cert dir structure (server/client/ca) with placeholder files."""
    certs = tmp_path / "certs"
    for sub in ("server", "client", "ca"):
        (certs / sub).mkdir(parents=True)
    for name in (
        "server/chunk-retriever.crt",
        "server/chunk-retriever.key",
        "client/chunk-writer.crt",
        "client/chunk-writer.key",
        "ca/ca.crt",
    ):
        (certs / name).write_text("")
    return certs


def test_cli_help() -> None:
    """Main help and subcommand help work."""
    r = _run_cli("--help")
    assert r.returncode == 0
    assert "generate" in r.stdout
    assert "validate" in r.stdout
    assert "show-schema" in r.stdout
    assert "test-connection" in r.stdout

    r = _run_cli("generate", "--help")
    assert r.returncode == 0
    assert "--output" in r.stdout
    assert "--certs-dir" in r.stdout
    assert "--base-url" in r.stdout

    r = _run_cli("validate", "--help")
    assert r.returncode == 0
    assert "CONFIG" in r.stdout

    r = _run_cli("show-schema", "--help")
    assert r.returncode == 0

    r = _run_cli("test-connection", "--help")
    assert r.returncode == 0
    assert "--config" in r.stdout


def test_cli_show_schema() -> None:
    """show-schema prints valid JSON schema with database_client."""
    r = _run_cli("show-schema")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert "database_client" in data.get("properties", {})
    assert data["properties"]["database_client"]["required"] == [
        "base_url",
        "client_cert_file",
        "client_key_file",
        "ca_cert_file",
    ]


def test_cli_generate_produces_valid_structure(tmp_path: Path) -> None:
    """Generate config to a file; output has database_client section and base_url."""
    certs = _make_certs_dir(tmp_path)
    out = tmp_path / "database_client_config.json"
    r = _run_cli(
        "generate",
        "--output",
        str(out),
        "--certs-dir",
        str(certs),
        "--base-url",
        "https://db.example:8017",
    )
    assert r.returncode == 0, (r.stdout, r.stderr)
    assert out.is_file()
    data = json.loads(out.read_text())
    assert "database_client" in data
    assert data["database_client"]["base_url"] == "https://db.example:8017"
    assert "client" in data
    assert data["client"].get("protocol") == "mtls"


def test_cli_validate_invalid_file(tmp_path: Path) -> None:
    """Validate exits non-zero for missing or invalid config."""
    missing = tmp_path / "missing.json"
    r = _run_cli("validate", str(missing))
    assert r.returncode != 0
    r = _run_cli("validate", str(missing), "--quiet")
    assert r.returncode != 0

    bad = tmp_path / "bad.json"
    bad.write_text("{")
    r = _run_cli("validate", str(bad))
    assert r.returncode != 0


def test_cli_validate_missing_database_client_section(tmp_path: Path) -> None:
    """Validate fails when database_client section is missing."""
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"client": {"enabled": False}}))
    r = _run_cli("validate", str(config))
    assert r.returncode != 0
    assert "database_client" in r.stderr


def test_cli_test_connection_valid_config_fails_connection(tmp_path: Path) -> None:
    """test-connection validates then tries connection; fails if server unreachable."""
    certs = _make_certs_dir(tmp_path)
    out = tmp_path / "database_client_config.json"
    r = _run_cli(
        "generate",
        "--output",
        str(out),
        "--certs-dir",
        str(certs),
        "--base-url",
        "https://localhost:19999",
    )
    assert r.returncode == 0
    r = _run_cli("test-connection", "--config", str(out))
    assert r.returncode != 0
    assert (
        "Connection test failed" in r.stderr
        or "Transport" in r.stderr
        or "connection" in r.stderr.lower()
    )


def test_cli_test_connection_nonexistent_config() -> None:
    """test-connection exits non-zero when config file does not exist."""
    r = _run_cli(
        "test-connection", "--config", "/nonexistent/database_client_config.json"
    )
    assert r.returncode != 0
    assert "not found" in r.stderr
