"""
Unit tests for config.py: load from file and env,
required/optional fields, defaults.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from ollama_workstation.config import (  # noqa: E402
    load_config,
    WorkstationConfig,
    DEFAULT_MAX_TOOL_ROUNDS,
    DEFAULT_OLLAMA_TIMEOUT,
)


def test_load_config_from_env() -> None:
    """Required fields from env; defaults for optional."""
    os.environ["OLLAMA_WORKSTATION_MCP_PROXY_URL"] = "http://proxy:3004"
    os.environ["OLLAMA_WORKSTATION_OLLAMA_BASE_URL"] = "http://ollama:11434"
    os.environ["OLLAMA_WORKSTATION_OLLAMA_MODEL"] = "qwen3"
    try:
        cfg = load_config(None)
        assert cfg.mcp_proxy_url == "http://proxy:3004"
        assert cfg.ollama_base_url == "http://ollama:11434"
        assert cfg.ollama_model == "qwen3"
        assert cfg.max_tool_rounds == DEFAULT_MAX_TOOL_ROUNDS
        assert cfg.ollama_timeout == DEFAULT_OLLAMA_TIMEOUT
    finally:
        for k in list(os.environ.keys()):
            if k.startswith("OLLAMA_WORKSTATION_"):
                del os.environ[k]


def test_load_config_from_json_file() -> None:
    """Load from JSON file; env overrides."""
    data = (
        '{"mcp_proxy_url":"http://p:1",'
        '"ollama_base_url":"http://o:2","ollama_model":"m"}'
    )
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        f.write(data.encode())
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg.mcp_proxy_url == "http://p:1"
        assert cfg.ollama_base_url == "http://o:2"
        assert cfg.ollama_model == "m"
    finally:
        Path(path).unlink(missing_ok=True)


def test_load_config_ignores_ollama_models_extra_key() -> None:
    """Config with ollama_models in ollama_workstation loads; extra key ok."""
    data = (
        '{"ollama_workstation":{"mcp_proxy_url":"http://p:1",'
        '"ollama_base_url":"http://o:2","ollama_model":"m",'
        '"ollama_models":["llama3.2","qwen3"]}}'
    )
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        f.write(data.encode())
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg.mcp_proxy_url == "http://p:1"
        assert cfg.ollama_model == "m"
    finally:
        Path(path).unlink(missing_ok=True)


def test_load_config_optional_fields_and_defaults() -> None:
    """Optional ollama_timeout and max_tool_rounds get defaults."""
    os.environ["OLLAMA_WORKSTATION_MCP_PROXY_URL"] = "http://x:1"
    os.environ["OLLAMA_WORKSTATION_OLLAMA_BASE_URL"] = "http://y:2"
    os.environ["OLLAMA_WORKSTATION_OLLAMA_MODEL"] = "z"
    try:
        cfg = load_config(None)
        assert cfg.ollama_timeout == DEFAULT_OLLAMA_TIMEOUT
        assert cfg.max_tool_rounds == DEFAULT_MAX_TOOL_ROUNDS
    finally:
        for k in list(os.environ.keys()):
            if k.startswith("OLLAMA_WORKSTATION_"):
                del os.environ[k]


def test_config_validation_required() -> None:
    """Missing required fields raise ValueError."""
    with pytest.raises(ValueError, match="mcp_proxy_url"):
        WorkstationConfig(
            mcp_proxy_url="",
            ollama_base_url="http://o:2",
            ollama_model="m",
        )
    with pytest.raises(ValueError, match="ollama_model"):
        WorkstationConfig(
            mcp_proxy_url="http://p:1",
            ollama_base_url="http://o:2",
            ollama_model="",
        )
