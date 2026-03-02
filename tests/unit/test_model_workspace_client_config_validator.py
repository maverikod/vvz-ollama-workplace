"""
Unit tests for model_workspace_client config validator.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import json
from pathlib import Path

import pytest

from model_workspace_client.config_validator import (
    ModelWorkspaceClientConfigError,
    validate_config,
    validate_config_dict,
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


def test_validate_config_dict_missing_model_workspace_client() -> None:
    """Missing model_workspace_client section yields error."""
    errors = validate_config_dict({})
    assert any("model_workspace_client" in path for path, _ in errors)
    assert any("required" in msg for _, msg in errors)


def test_validate_config_dict_valid_minimal() -> None:
    """Valid minimal model_workspace_client (ws) returns no errors."""
    config = {
        "model_workspace_client": {
            "ws_endpoint": "ws://localhost:8016",
        },
        "client": {"enabled": False},
    }
    errors = validate_config_dict(config)
    assert errors == []


def test_validate_config_dict_wss_requires_certs(tmp_path: Path) -> None:
    """wss:// endpoint without cert paths yields errors."""
    config = {
        "model_workspace_client": {
            "ws_endpoint": "wss://model-workspace-server:8016",
        },
        "client": {"enabled": False},
    }
    errors = validate_config_dict(config)
    assert any("client_cert_file" in path or "required" in msg for path, msg in errors)


def test_validate_config_dict_wss_with_certs(tmp_path: Path) -> None:
    """wss with cert files and client mtls passes dict validation."""
    certs = _make_certs_dir(tmp_path)
    config = {
        "model_workspace_client": {
            "ws_endpoint": "wss://model-workspace-server:8016",
            "client_cert_file": str(certs / "client" / "mcp-proxy.crt"),
            "client_key_file": str(certs / "client" / "mcp-proxy.key"),
            "ca_cert_file": str(certs / "ca" / "ca.crt"),
        },
        "client": {
            "enabled": True,
            "protocol": "mtls",
            "ssl": {
                "cert": str(certs / "client" / "mcp-proxy.crt"),
                "key": str(certs / "client" / "mcp-proxy.key"),
                "ca": str(certs / "ca" / "ca.crt"),
            },
        },
    }
    errors = validate_config_dict(config)
    assert errors == []


def test_validate_config_dict_invalid_ws_scheme() -> None:
    """http:// in ws_endpoint yields error."""
    config = {
        "model_workspace_client": {"ws_endpoint": "http://localhost:8016"},
    }
    errors = validate_config_dict(config)
    assert any("ws" in msg or "wss" in msg for _, msg in errors)


def test_validate_config_dict_empty_ws_endpoint() -> None:
    """Empty ws_endpoint yields error."""
    config = {
        "model_workspace_client": {"ws_endpoint": ""},
    }
    errors = validate_config_dict(config)
    assert any("ws_endpoint" in path for path, _ in errors)


def test_validate_config_dict_negative_timeout() -> None:
    """Negative connect_timeout_seconds yields error."""
    config = {
        "model_workspace_client": {
            "ws_endpoint": "ws://localhost:8016",
            "connect_timeout_seconds": 0,
        },
    }
    errors = validate_config_dict(config)
    assert any("connect_timeout" in path for path, _ in errors)


def test_validate_config_dict_negative_retry_backoff() -> None:
    """Negative retry_backoff_seconds yields error."""
    config = {
        "model_workspace_client": {
            "ws_endpoint": "ws://localhost:8016",
            "retry_backoff_seconds": -1,
        },
    }
    errors = validate_config_dict(config)
    assert any("retry_backoff" in path for path, _ in errors)


def test_validate_config_dict_client_mtls_missing_ssl(tmp_path: Path) -> None:
    """client enabled mtls without ssl section yields errors."""
    config = {
        "model_workspace_client": {"ws_endpoint": "ws://localhost:8016"},
        "client": {"enabled": True, "protocol": "mtls"},
    }
    errors = validate_config_dict(config)
    assert any("client" in path and "ssl" in path for path, _ in errors)


def test_validate_config_file_not_found() -> None:
    """validate_config raises on missing file."""
    with pytest.raises(ModelWorkspaceClientConfigError) as exc_info:
        validate_config(Path("/nonexistent/config.json"))
    assert "config_path" in exc_info.value.errors[0][0]
    assert "not found" in exc_info.value.errors[0][1]


def test_validate_config_invalid_json(tmp_path: Path) -> None:
    """validate_config raises on invalid JSON."""
    bad = tmp_path / "bad.json"
    bad.write_text("not json")
    with pytest.raises(ModelWorkspaceClientConfigError) as exc_info:
        validate_config(bad)
    assert any("JSON" in msg for _, msg in exc_info.value.errors)


def test_validate_config_valid_file(tmp_path: Path) -> None:
    """Generated config passes client validation; adapter may reject empty PEMs."""
    from model_workspace_client.config_generator import generate_client_config

    certs = _make_certs_dir(tmp_path)
    out_file = tmp_path / "config.json"
    generate_client_config(
        {
            "output_path": out_file,
            "certs_dir": str(certs),
            "ws_endpoint": "wss://model-workspace-server:8016",
        }
    )
    try:
        validate_config(out_file)
    except ModelWorkspaceClientConfigError as e:
        # Adapter may reject placeholder certs (invalid PEM);
        # client errors must be empty.
        client_errors = [(p, m) for p, m in e.errors if p != "adapter"]
        assert not client_errors, f"client validation should pass: {client_errors}"


def test_validate_config_missing_section_raises(tmp_path: Path) -> None:
    """validate_config raises when model_workspace_client missing."""
    config = {"server": {}, "client": {"enabled": False}}
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ModelWorkspaceClientConfigError) as exc_info:
        validate_config(path)
    assert any("model_workspace_client" in path for path, _ in exc_info.value.errors)


def test_error_messages() -> None:
    """ModelWorkspaceClientConfigError.messages() returns list of strings."""
    err = ModelWorkspaceClientConfigError([("a.b", "msg1"), ("c", "msg2")])
    assert err.errors == [("a.b", "msg1"), ("c", "msg2")]
    assert "a.b" in err.messages()[0]
    assert "msg1" in err.messages()[0]
