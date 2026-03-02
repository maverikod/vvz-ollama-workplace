"""
Unit tests for model_workspace_server config generator.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import json
from pathlib import Path

import pytest

from model_workspace_server.config_generator import (
    generate_server_config,
    merge_settings,
)


def _make_certs_dir(tmp_path: Path) -> Path:
    """Create minimal cert dir structure (server/client/ca) with placeholder files."""
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


def test_merge_settings_template_only() -> None:
    """merge_settings returns template when no overlays."""
    t = {"a": 1, "b": 2}
    assert merge_settings(t) == t
    assert merge_settings(t, {}, {}) == t


def test_merge_settings_args_override_env_override_template() -> None:
    """Later overlay wins: template < env < args."""
    t = {"a": 1, "b": 2}
    env = {"b": 20}
    args = {"a": 10}
    out = merge_settings(t, env, args)
    assert out["a"] == 10
    assert out["b"] == 20


def test_merge_settings_skips_empty_overlay_values() -> None:
    """Empty string and None in overlay do not overwrite template."""
    t = {"a": 1}
    env = {"a": "", "b": None}
    out = merge_settings(t, env)
    assert out["a"] == 1
    assert "b" not in out


def test_generate_server_config_writes_ws_ready_config(tmp_path: Path) -> None:
    """One command generates valid config with WS-ready section."""
    certs = _make_certs_dir(tmp_path)
    out_file = tmp_path / "model_workspace_server_config.json"
    settings = {
        "output_path": out_file,
        "certs_dir": str(certs),
        "server_port": 8016,
        "advertised_host": "test-mws",
        "log_dir": str(tmp_path / "logs"),
        "transport_type": "ws",
        "fallback_policy": "deny",
    }
    generate_server_config(settings)
    assert out_file.is_file()
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert "server" in data
    assert data["server"].get("advertised_host") == "test-mws"
    assert data["server"].get("log_dir") == str(tmp_path / "logs")
    assert "transport" in data
    assert data["transport"].get("transport_type") == "ws"
    assert data["transport"].get("fallback_policy") == "deny"
    assert data["transport"].get("verify_client") is True
    assert "model_workspace_server" in data
    mws = data["model_workspace_server"]
    assert "runtime_identity" in mws
    assert "instance_uuid" in mws["runtime_identity"]
    assert mws["runtime_identity"].get("server_id") == "test-mws"
    assert "limits" in mws
    assert mws["limits"].get("max_connections") == 100
    assert mws.get("log_dir") == str(tmp_path / "logs")
    assert "registration" in data


def test_generate_server_config_requires_output_path() -> None:
    """generate_server_config raises when output_path is missing."""
    with pytest.raises(ValueError, match="output_path"):
        generate_server_config(
            {
                "certs_dir": "/nonexistent",
                "server_port": 8016,
                "advertised_host": "x",
                "log_dir": "/app/logs",
            }
        )
