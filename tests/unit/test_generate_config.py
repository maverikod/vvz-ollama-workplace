"""
Unit tests for docker generate_config: ollama_models in generated config.

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


def test_generate_config_includes_ollama_models(tmp_path: Path) -> None:
    """Generated config contains ollama_models list from env."""
    certs = tmp_path / "certs"
    certs.mkdir()
    for name in (
        "ca.crt", "server.crt", "server.key", "client.crt", "client.key"
    ):
        (certs / name).write_text("")

    config_path = tmp_path / "adapter_config.json"
    env = {
        "ADAPTER_CONFIG_PATH": str(config_path),
        "CERTS_DIR": str(certs),
        "ADVERTISED_HOST": "test-adapter",
        "OLLAMA_MODELS": "llama3.2,qwen3",
    }
    saved = {k: os.environ.get(k) for k in env}
    try:
        os.environ.update(env)
        import generate_config as gen  # noqa: E402

        gen.main()
        data = json.loads(config_path.read_text())
        ow = data.get("ollama_workstation") or {}
        assert "ollama_models" in ow
        assert ow["ollama_models"] == ["llama3.2", "qwen3"]
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_generate_config_ollama_models_default(tmp_path: Path) -> None:
    """Default OLLAMA_MODELS yields single default model in list."""
    certs = tmp_path / "certs"
    certs.mkdir()
    for name in (
        "ca.crt", "server.crt", "server.key", "client.crt", "client.key"
    ):
        (certs / name).write_text("")

    config_path = tmp_path / "adapter_config.json"
    env = {
        "ADAPTER_CONFIG_PATH": str(config_path),
        "CERTS_DIR": str(certs),
        "ADVERTISED_HOST": "test-adapter",
    }
    saved = {k: os.environ.get(k) for k in env}
    try:
        os.environ.pop("OLLAMA_MODELS", None)
        os.environ.update(env)
        import generate_config as gen  # noqa: E402

        importlib.reload(gen)
        gen.main()
        data = json.loads(config_path.read_text())
        ow = data.get("ollama_workstation") or {}
        assert "ollama_models" in ow
        assert ow["ollama_models"] == ["llama3.2"]
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        os.environ.pop("OLLAMA_MODELS", None)
