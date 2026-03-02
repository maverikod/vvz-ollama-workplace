"""
Unit tests for model_workspace_client config generator.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import json
from pathlib import Path

import pytest

from model_workspace_client.config_generator import (
    generate_client_config,
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
        "client/mcp-proxy.crt",
        "client/mcp-proxy.key",
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


def test_generate_client_config_writes_consumable_config(tmp_path: Path) -> None:
    """Generated config is directly consumable by client package."""
    certs = _make_certs_dir(tmp_path)
    out_file = tmp_path / "model_workspace_client_config.json"
    settings = {
        "output_path": out_file,
        "certs_dir": str(certs),
        "ws_endpoint": "wss://model-workspace-server:8016",
        "connect_timeout_seconds": 15,
        "request_timeout_seconds": 90,
        "retry_max_attempts": 5,
        "log_level": "DEBUG",
    }
    generate_client_config(settings)
    assert out_file.is_file()
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert "client" in data
    assert data["client"].get("enabled") is True
    assert data["client"].get("protocol") == "mtls"
    assert "ssl" in data["client"]
    assert data["client"]["ssl"].get("cert") == str(certs / "client" / "mcp-proxy.crt")
    assert "model_workspace_client" in data
    mwc = data["model_workspace_client"]
    assert mwc.get("ws_endpoint") == "wss://model-workspace-server:8016"
    assert mwc.get("connect_timeout_seconds") == 15
    assert mwc.get("request_timeout_seconds") == 90
    assert mwc.get("retry_max_attempts") == 5
    assert "observability" in mwc
    assert mwc["observability"].get("log_level") == "DEBUG"


def test_generate_client_config_requires_output_path() -> None:
    """generate_client_config raises when output_path is missing."""
    with pytest.raises(ValueError, match="output_path"):
        generate_client_config(
            {
                "certs_dir": "/nonexistent",
                "ws_endpoint": "wss://localhost:8016",
            }
        )


def test_generate_client_config_requires_ws_endpoint(tmp_path: Path) -> None:
    """generate_client_config raises when ws_endpoint is missing or empty."""
    certs = _make_certs_dir(tmp_path)
    out_file = tmp_path / "out.json"
    with pytest.raises(ValueError, match="ws_endpoint"):
        generate_client_config(
            {
                "output_path": out_file,
                "certs_dir": str(certs),
                "ws_endpoint": "",
            }
        )


def test_generate_client_config_uses_adapter_base_generator(tmp_path: Path) -> None:
    """
    Config is built on adapter base: base structure comes from SimpleConfigGenerator.

    Asserts presence of top-level sections and key fields that only the adapter
    base generator produces (server, registration, server_validation, auth,
    queue_manager, transport). Overlay sections client and model_workspace_client
    are asserted in test_generate_client_config_writes_consumable_config.
    """
    certs = _make_certs_dir(tmp_path)
    out_file = tmp_path / "model_workspace_client_config.json"
    generate_client_config(
        {
            "output_path": out_file,
            "certs_dir": str(certs),
            "ws_endpoint": "wss://model-workspace-server:8016",
        }
    )
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert "server" in data, "adapter base produces server section"
    assert "host" in data["server"] or "port" in data["server"]
    assert "ssl" in data["server"]
    assert "registration" in data, "adapter base produces registration section"
    assert "heartbeat" in data["registration"] or "register_url" in data["registration"]
    assert "ssl" in data["registration"]
    assert "server_validation" in data, "adapter base produces server_validation"
    assert "auth" in data, "adapter base produces auth section"
    assert "queue_manager" in data, "adapter base produces queue_manager section"
    assert "client" in data, "overlay: client section"
    assert "model_workspace_client" in data, "overlay: model_workspace_client section"
