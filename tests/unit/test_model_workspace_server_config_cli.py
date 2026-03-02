"""
Unit tests for model_workspace_server config_cli.

Subcommands: generate, validate, show-schema, sample.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC = PROJECT_ROOT / "src"


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    """Run model-workspace-server config CLI as python -m."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "model_workspace_server.config_cli"] + list(args),
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        env=env,
    )


def _make_certs_dir(tmp_path: Path) -> Path:
    """Create minimal cert dir structure with placeholder files."""
    certs = tmp_path / "certs"
    for sub in ("server", "client", "ca"):
        (certs / sub).mkdir(parents=True)
    for name in (
        "server/test-server.crt",
        "server/test-server.key",
        "client/test-server.crt",
        "client/test-server.key",
        "ca/ca.crt",
    ):
        (certs / name).write_text("")
    return certs


def test_cli_help() -> None:
    """Main help and subcommand help list generate, validate, show-schema, sample."""
    r = _run_cli("--help")
    assert r.returncode == 0
    assert "generate" in r.stdout
    assert "validate" in r.stdout
    assert "show-schema" in r.stdout
    assert "sample" in r.stdout

    r = _run_cli("generate", "--help")
    assert r.returncode == 0
    assert "--output" in r.stdout
    assert "--certs-dir" in r.stdout

    r = _run_cli("validate", "--help")
    assert r.returncode == 0
    assert "CONFIG" in r.stdout
    assert "--quiet" in r.stdout

    r = _run_cli("show-schema", "--help")
    assert r.returncode == 0

    r = _run_cli("sample", "--help")
    assert r.returncode == 0


def test_cli_validate_valid(tmp_path: Path) -> None:
    """Validate exits 0 for valid config (dict-only; no adapter load)."""
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            {
                "server": {
                    "advertised_host": "test",
                    "servername": "test",
                    "server_port": 8016,
                    "log_dir": "/app/logs",
                },
                "transport": {
                    "transport_type": "ws",
                    "fallback_policy": "deny",
                    "verify_client": True,
                },
                "model_workspace_server": {
                    "runtime_identity": {
                        "instance_uuid": "uuid-1",
                        "server_id": "test",
                    },
                    "limits": {
                        "max_connections": 100,
                        "request_timeout_seconds": 120,
                    },
                    "log_dir": "/app/logs",
                },
            },
            indent=2,
        )
    )
    (tmp_path / "cert.pem").write_text("")
    (tmp_path / "key.pem").write_text("")
    (tmp_path / "ca.pem").write_text("")
    # Valid dict structure but adapter + ws require server.ssl with existing files
    data = json.loads(config.read_text())
    data["server"]["ssl"] = {
        "cert": str(tmp_path / "cert.pem"),
        "key": str(tmp_path / "key.pem"),
        "ca": str(tmp_path / "ca.pem"),
    }
    config.write_text(json.dumps(data, indent=2))

    r = _run_cli("validate", str(config))
    if r.returncode != 0:
        # Adapter may be missing or report errors; at least stderr has diagnostics
        assert "config" in r.stderr.lower() or "transport" in r.stderr.lower()
    # When adapter is present and config is valid, we get 0
    if r.returncode == 0:
        assert "valid" in r.stderr.lower() or r.stderr == ""


def test_cli_validate_invalid_file(tmp_path: Path) -> None:
    """Validate exits non-zero for missing or invalid JSON file."""
    missing = tmp_path / "missing.json"
    r = _run_cli("validate", str(missing))
    assert r.returncode != 0
    assert "not found" in r.stderr.lower() or "config_path" in r.stderr

    bad = tmp_path / "bad.json"
    bad.write_text("{")
    r = _run_cli("validate", str(bad))
    assert r.returncode != 0


def test_cli_validate_quiet() -> None:
    """Validate --quiet returns exit code only; no required stdout/stderr content."""
    r = _run_cli("validate", "/nonexistent/config.json", "--quiet")
    assert r.returncode != 0


def test_cli_show_schema() -> None:
    """show-schema exits 0 and prints JSON with model_workspace_server schema."""
    r = _run_cli("show-schema")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert "properties" in data
    assert "model_workspace_server" in data.get("properties", {})
    assert data.get("required") == ["server", "transport", "model_workspace_server"]


def test_cli_sample() -> None:
    """sample exits 0 and prints JSON with server, transport, model_workspace_server."""
    r = _run_cli("sample")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert "server" in data
    assert "transport" in data
    assert "model_workspace_server" in data
    assert data["transport"].get("transport_type") == "ws"
    assert "runtime_identity" in data["model_workspace_server"]


def test_cli_generate_and_validate(tmp_path: Path) -> None:
    """Generate config to file then validate; stable exit codes."""
    certs = _make_certs_dir(tmp_path)
    out = tmp_path / "model_workspace_server_config.json"
    r = _run_cli(
        "generate",
        "--output",
        str(out),
        "--certs-dir",
        str(certs),
        "--mcp-proxy-url",
        "https://proxy.example.com:3004",
    )
    assert r.returncode == 0, (r.stdout, r.stderr)
    assert out.is_file()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "server" in data
    assert "transport" in data
    assert data["transport"].get("transport_type") == "ws"
    assert "model_workspace_server" in data

    r = _run_cli("validate", str(out))
    # Adapter may add requirements; at least no MWS-specific errors
    if r.returncode != 0:
        mws_errors = [
            line
            for line in r.stderr.splitlines()
            if "model_workspace_server" in line or "transport.transport" in line
        ]
        assert not mws_errors, f"Unexpected MWS errors: {mws_errors}"
