"""
Unit tests for database_client config generator.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import json
from pathlib import Path
from typing import Any

import pytest

from database_client.config_generator import (
    _default_client_template,
    generate_client_config,
    generate_from_merged,
    merge_settings,
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


def test_default_client_template_has_expected_keys() -> None:
    """Default template contains endpoint, certs, retry, timeouts."""
    t = _default_client_template(Path("mtls_certificates"))
    assert "output_path" in t
    assert "certs_dir" in t
    assert "base_url" in t
    assert "client_cert_file" in t
    assert "client_key_file" in t
    assert "ca_cert_file" in t
    assert "connect_timeout_seconds" in t
    assert "request_timeout_seconds" in t
    assert "retry_max_attempts" in t
    assert "retry_backoff_seconds" in t
    assert "log_level" in t
    assert "metrics_enabled" in t


def test_generate_from_merged_writes_config(tmp_path: Path) -> None:
    """generate_from_merged produces valid config with args overlay."""
    certs = _make_certs_dir(tmp_path)
    out_file = tmp_path / "generated_client.json"
    generate_from_merged(
        args_overlay={
            "output_path": str(out_file),
            "certs_dir": str(certs),
            "base_url": "https://db.example.com:8017",
        }
    )
    assert out_file.is_file()
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert (
        data.get("database_client", {}).get("base_url") == "https://db.example.com:8017"
    )
    assert data.get("client", {}).get("protocol") == "mtls"


def test_generate_from_merged_default_output_path(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """When output_path not set, default path is config/database_client_config.json."""
    monkeypatch.chdir(tmp_path)
    certs = _make_certs_dir(tmp_path)
    (tmp_path / "config").mkdir(exist_ok=True)
    generate_from_merged(
        args_overlay={
            "certs_dir": str(certs),
            "base_url": "https://localhost:8017",
        }
    )
    default_path = tmp_path / "config" / "database_client_config.json"
    assert default_path.is_file()


def test_generate_client_config_writes_consumable_config(tmp_path: Path) -> None:
    """Generated config is directly usable by database_client package."""
    certs = _make_certs_dir(tmp_path)
    out_file = tmp_path / "database_client_config.json"
    settings = {
        "output_path": out_file,
        "certs_dir": str(certs),
        "base_url": "https://database-server:8017",
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
    assert data["client"]["ssl"].get("cert") == str(
        certs / "client" / "chunk-writer.crt"
    )
    assert "database_client" in data
    dc = data["database_client"]
    assert dc.get("base_url") == "https://database-server:8017"
    assert dc.get("connect_timeout_seconds") == 15
    assert dc.get("request_timeout_seconds") == 90
    assert dc.get("retry_max_attempts") == 5
    assert "observability" in dc
    assert dc["observability"].get("log_level") == "DEBUG"


def test_generate_client_config_requires_output_path() -> None:
    """generate_client_config raises when output_path is missing."""
    with pytest.raises(ValueError, match="output_path"):
        generate_client_config(
            {
                "certs_dir": "/nonexistent",
                "base_url": "https://database-server:8017",
            }
        )


def test_generate_client_config_requires_base_url(tmp_path: Path) -> None:
    """generate_client_config raises when base_url is missing or empty."""
    certs = _make_certs_dir(tmp_path)
    out_file = tmp_path / "out.json"
    with pytest.raises(ValueError, match="base_url"):
        generate_client_config(
            {
                "output_path": out_file,
                "certs_dir": str(certs),
                "base_url": "",
            }
        )


def test_generate_client_config_adapter_contract_sections(tmp_path: Path) -> None:
    """Config has adapter sections: client, server_validation, auth, database_client."""
    certs = _make_certs_dir(tmp_path)
    out_file = tmp_path / "database_client_config.json"
    generate_client_config(
        {
            "output_path": out_file,
            "certs_dir": str(certs),
            "base_url": "https://database-server:8017",
        }
    )
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert "client" in data
    assert "server_validation" in data
    assert "auth" in data
    assert "database_client" in data
    assert data["client"]["protocol"] == "mtls"
    assert data["database_client"]["base_url"] == "https://database-server:8017"


def test_generate_client_config_uses_adapter_base_generator(tmp_path: Path) -> None:
    """
    Config is built on adapter base: base structure comes from SimpleConfigGenerator.

    Asserts presence of top-level sections and key fields that only the adapter
    base generator produces (server, registration, server_validation, auth,
    queue_manager). Overlay sections client and database_client are asserted
    in test_generate_client_config_writes_consumable_config.
    """
    certs = _make_certs_dir(tmp_path)
    out_file = tmp_path / "database_client_config.json"
    generate_client_config(
        {
            "output_path": out_file,
            "certs_dir": str(certs),
            "base_url": "https://database-server:8017",
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
    assert "database_client" in data, "overlay: database_client section"
