"""
Unit tests for docker generate_config: mwps_models in generated config.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import importlib
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "docker"))


def test_generate_config_includes_mwps_models(tmp_path: Path) -> None:
    """Generated config contains mwps_models list from env."""
    certs = tmp_path / "certs"
    certs.mkdir()
    for name in ("ca.crt", "server.crt", "server.key", "client.crt", "client.key"):
        (certs / name).write_text("")

    config_path = tmp_path / "adapter_config.json"
    env = {
        "ADAPTER_CONFIG_PATH": str(config_path),
        "CERTS_DIR": str(certs),
        "ADVERTISED_HOST": "test-adapter",
        "MWPS_PRELOAD_MODELS": "llama3.2,qwen3",
    }
    saved = {k: os.environ.get(k) for k in env}
    try:
        os.environ.update(env)
        import generate_config as gen  # noqa: E402

        gen.main()
        data = json.loads(config_path.read_text())
        ow = data.get("mwps") or {}
        assert "mwps" in ow
        assert isinstance(ow["mwps"], dict)
        assert ow["mwps"].get("models") == ["llama3.2", "qwen3"]
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_generate_config_mwps_models_default(tmp_path: Path) -> None:
    """Default MWPS_PRELOAD_MODELS yields single default model in list."""
    certs = tmp_path / "certs"
    certs.mkdir()
    for name in ("ca.crt", "server.crt", "server.key", "client.crt", "client.key"):
        (certs / name).write_text("")

    config_path = tmp_path / "adapter_config.json"
    env = {
        "ADAPTER_CONFIG_PATH": str(config_path),
        "CERTS_DIR": str(certs),
        "ADVERTISED_HOST": "test-adapter",
    }
    saved = {k: os.environ.get(k) for k in env}
    try:
        os.environ.pop("MWPS_PRELOAD_MODELS", None)
        os.environ.update(env)
        import generate_config as gen  # noqa: E402

        importlib.reload(gen)
        gen.main()
        data = json.loads(config_path.read_text())
        ow = data.get("mwps") or {}
        assert "mwps" in ow
        assert ow["mwps"].get("models") == ["llama3.2"]
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        os.environ.pop("MWPS_PRELOAD_MODELS", None)


def test_generate_config_context_paths_included(tmp_path: Path) -> None:
    """Generated config includes standards_file_path and rules_file_path for context."""
    certs = tmp_path / "certs"
    certs.mkdir()
    for name in ("ca.crt", "server.crt", "server.key", "client.crt", "client.key"):
        (certs / name).write_text("")

    config_path = tmp_path / "adapter_config.json"
    from mwps.config_generator_core import generate_adapter_config

    generate_adapter_config(
        {
            "output_path": config_path,
            "certs_dir": certs,
            "server_port": 8015,
            "mcp_proxy_host": "p",
            "mcp_proxy_port": 3004,
            "advertised_host": "h",
            "log_dir": str(tmp_path),
            "mwps_base_url": "http://127.0.0.1:11434",
            "model_server_url": "http://127.0.0.1:11434",
            "mwps_model": "llama3.2",
            "mwps_models": ["llama3.2"],
            "standards_file_path": "config/standards.md",
            "rules_file_path": "config/rules.md",
        }
    )
    data = json.loads(config_path.read_text())
    ow = data.get("mwps") or {}
    assert ow.get("standards_file_path") == "config/standards.md"
    assert ow.get("rules_file_path") == "config/rules.md"


def _run_adapter_extract_models(ow: dict) -> tuple[list[str], str]:
    """Same extraction logic as docker/run_adapter.py for model list and URL."""
    oo = (ow.get("mwps") or {}) if isinstance(ow, dict) else {}
    model_list = list(oo.get("models") or [])
    if not model_list and oo.get("model"):
        model_list = [str(oo.get("model", "")).strip()]
    model_list = [m for m in model_list if isinstance(m, str) and m.strip()]
    model_server_url = (
        oo.get("model_server_url") or oo.get("base_url") or "http://127.0.0.1:11434"
    ).strip()
    return model_list, model_server_url


def test_run_adapter_extracts_models_from_generated_config(tmp_path: Path) -> None:
    """run_adapter-style extraction from generated config yields correct model list."""
    certs = tmp_path / "certs"
    certs.mkdir()
    for name in ("ca.crt", "server.crt", "server.key", "client.crt", "client.key"):
        (certs / name).write_text("")

    config_path = tmp_path / "adapter_config.json"
    env = {
        "ADAPTER_CONFIG_PATH": str(config_path),
        "CERTS_DIR": str(certs),
        "ADVERTISED_HOST": "test-adapter",
        "MWPS_PRELOAD_MODELS": "llama3.2,qwen3,qwen2.5-coder:1.5b",
    }
    saved = {k: os.environ.get(k) for k in env}
    try:
        os.environ.update(env)
        import generate_config as gen  # noqa: E402

        importlib.reload(gen)
        gen.main()
        assert (
            config_path.exists()
        ), "generate_config should write to ADAPTER_CONFIG_PATH"
        data = json.loads(config_path.read_text())
        ow = data.get("mwps") or {}
        model_list, model_server_url = _run_adapter_extract_models(ow)
        assert model_list == ["llama3.2", "qwen3", "qwen2.5-coder:1.5b"]
        assert model_server_url == "http://127.0.0.1:11434"
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
