"""
Unit tests for config_cli (generate and validate subcommands).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    exe = PROJECT_ROOT / ".venv" / "bin" / "config-cli"
    if not exe.exists():
        exe = sys.executable
        args = ("-m", "ollama_workstation.config_cli") + args
    return subprocess.run(
        [str(exe)] + list(args),
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )


def test_cli_help() -> None:
    """Main help and subcommand help work."""
    r = _run_cli("--help")
    assert r.returncode == 0
    assert "generate" in r.stdout
    assert "validate" in r.stdout

    r = _run_cli("generate", "--help")
    assert r.returncode == 0
    assert "--output" in r.stdout
    assert "--certs-dir" in r.stdout
    assert "--ollama-model" in r.stdout

    r = _run_cli("validate", "--help")
    assert r.returncode == 0
    assert "CONFIG" in r.stdout
    assert "--no-adapter" in r.stdout


def test_cli_generate_and_validate(tmp_path: Path) -> None:
    """Generate config to a file, then validate it (project-only)."""
    certs = tmp_path / "certs"
    certs.mkdir()
    for name in ("ca.crt", "server.crt", "server.key", "client.crt", "client.key"):
        (certs / name).write_text("")

    out = tmp_path / "adapter_config.json"
    r = _run_cli(
        "generate",
        "--output",
        str(out),
        "--certs-dir",
        str(certs),
        "--target",
        "docker",
    )
    assert r.returncode == 0, (r.stdout, r.stderr)
    assert out.is_file()
    data = json.loads(out.read_text())
    assert "ollama_workstation" in data
    ow = data["ollama_workstation"]
    assert "ollama" in ow and ow["ollama"].get("models") == ["llama3.2"]

    r = _run_cli("validate", str(out), "--no-adapter")
    assert r.returncode == 0, (r.stdout, r.stderr)


def test_cli_validate_invalid_json(tmp_path: Path) -> None:
    """Validate exits non-zero for invalid JSON."""
    bad = tmp_path / "bad.json"
    bad.write_text("{")
    r = _run_cli("validate", str(bad), "--no-adapter")
    assert r.returncode != 0
