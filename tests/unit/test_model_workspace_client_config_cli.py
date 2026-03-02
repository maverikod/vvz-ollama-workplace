"""
Unit tests for model_workspace_client config CLI.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import json
import sys
from pathlib import Path

import pytest

from model_workspace_client.config_cli import (
    EXIT_CONNECTION_ERROR,
    EXIT_OK,
    EXIT_VALIDATION_ERROR,
    _cmd_generate,
    _cmd_show_schema,
    _cmd_test_connection,
    _cmd_validate,
    _get_schema_doc,
    _ws_handshake_safe,
    main,
)


def _make_certs_dir(tmp_path: Path) -> Path:
    """Create minimal cert dir structure with placeholder files."""
    certs = tmp_path / "certs"
    for sub in ("server", "client", "ca"):
        (certs / sub).mkdir(parents=True)
    for name in (
        "server/test-server.crt",
        "server/test-server.key",
        "client/mcp-proxy.crt",
        "client/mcp-proxy.key",
        "ca/ca.crt",
    ):
        (certs / name).write_text("")
    return certs


def test_cli_help() -> None:
    """--help exits 0 and prints usage."""
    old_argv = sys.argv
    try:
        sys.argv = ["prog", "--help"]
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
    finally:
        sys.argv = old_argv


def test_cmd_validate_missing_file(capsys: pytest.CaptureFixture[str]) -> None:
    """validate with missing config file returns EXIT_VALIDATION_ERROR."""

    class Args:
        config = "/nonexistent_config_12345.json"
        quiet = False

    code = _cmd_validate(Args())
    assert code == EXIT_VALIDATION_ERROR
    out, err = capsys.readouterr()
    assert "not found" in err or "nonexistent" in err.lower()


def test_cmd_validate_invalid_client_section(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Invalid client config (wss no certs) -> EXIT_VALIDATION_ERROR."""
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "model_workspace_client": {"ws_endpoint": "wss://localhost:8016"},
                "client": {"enabled": False},
            }
        )
    )

    class Args:
        config = str(config_file)
        quiet = False

    code = _cmd_validate(Args())
    assert code == EXIT_VALIDATION_ERROR
    _, err = capsys.readouterr()
    assert "wss" in err or "required" in err or "client" in err.lower()


def test_cmd_show_schema_returns_valid_json(capsys: pytest.CaptureFixture[str]) -> None:
    """show-schema prints valid JSON with expected keys."""

    class Args:
        format = "json"

    code = _cmd_show_schema(Args())
    assert code == EXIT_OK
    out, _ = capsys.readouterr()
    schema = json.loads(out)
    assert "description" in schema
    assert "sections" in schema
    assert "model_workspace_client" in schema["sections"]
    assert "client" in schema["sections"]


def test_get_schema_doc_structure() -> None:
    """_get_schema_doc returns dict with required keys."""
    doc = _get_schema_doc()
    assert isinstance(doc, dict)
    assert "model_workspace_client" in doc.get("sections", {})
    assert "ws_endpoint" in doc["sections"]["model_workspace_client"].get("fields", {})


def test_cmd_generate_creates_file(tmp_path: Path) -> None:
    """generate writes config file and returns EXIT_OK."""
    certs = _make_certs_dir(tmp_path)
    out_file = tmp_path / "out_config.json"

    class Args:
        output = str(out_file)
        certs_dir = str(certs)
        ws_endpoint = "wss://test:8016"
        connect_timeout = 30
        request_timeout = 120
        retry_max = 3
        retry_backoff = 2.0
        log_level = "INFO"
        metrics_enabled = False

    code = _cmd_generate(Args())
    assert code == EXIT_OK
    assert out_file.is_file()
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert (
        data.get("model_workspace_client", {}).get("ws_endpoint") == "wss://test:8016"
    )


def test_cmd_test_connection_validates_first(tmp_path: Path) -> None:
    """test-connection runs validator first; invalid config -> EXIT_VALIDATION_ERROR."""
    config_file = tmp_path / "bad.json"
    config_file.write_text(
        json.dumps({"model_workspace_client": {}})
    )  # missing ws_endpoint

    class Args:
        config = str(config_file)
        quiet = True

    code = _cmd_test_connection(Args())
    assert code == EXIT_VALIDATION_ERROR


def test_cmd_test_connection_connection_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """test-connection with valid config, no server -> EXIT_CONNECTION_ERROR."""
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "model_workspace_client": {
                    "ws_endpoint": "ws://127.0.0.1:39999",
                    "connect_timeout_seconds": 2,
                },
                "client": {"enabled": False},
            }
        )
    )
    from model_workspace_client import config_cli

    monkeypatch.setattr(config_cli, "validate_config", lambda _: None)

    class Args:
        config = str(config_file)
        quiet = True

    code = _cmd_test_connection(Args())
    assert code == EXIT_CONNECTION_ERROR


def test_ws_handshake_safe_ws_connection_refused() -> None:
    """_ws_handshake_safe with ws:// to non-listening port returns (False, message)."""
    ok, msg = _ws_handshake_safe(
        "ws://127.0.0.1:39999",
        None,
        None,
        None,
        timeout_seconds=1,
    )
    assert ok is False
    assert "failed" in msg.lower() or "refused" in msg.lower() or "error" in msg.lower()


def test_ws_handshake_safe_wss_without_certs_returns_false() -> None:
    """_ws_handshake_safe with wss:// and no certs returns (False, message)."""
    ok, msg = _ws_handshake_safe(
        "wss://localhost:8016",
        None,
        None,
        None,
        timeout_seconds=5,
    )
    assert ok is False
    assert "wss requires" in msg or "client_cert" in msg
