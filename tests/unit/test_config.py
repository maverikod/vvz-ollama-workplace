"""
Unit tests for config.py: load from file and env,
required/optional fields, defaults.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import json
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
from ollama_workstation.docker_config_validation import (  # noqa: E402
    validate_project_config,
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


def test_load_config_commands_policy_section() -> None:
    """Config with allowed_commands, forbidden_commands, commands_policy (step 01)."""
    data = (
        '{"ollama_workstation":{"mcp_proxy_url":"http://p:1",'
        '"ollama_base_url":"http://o:2","ollama_model":"m",'
        '"commands_policy":"deny_by_default",'
        '"allowed_commands":["cmd.server"],"forbidden_commands":[]}}'
    )
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        f.write(data.encode())
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg.commands_policy_config is not None
        assert cfg.commands_policy_config.commands_policy == "deny_by_default"
        assert cfg.commands_policy_config.allowed_commands == ("cmd.server",)
        assert cfg.commands_policy_config.forbidden_commands == ()
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


def test_load_config_available_providers(tmp_path: Path) -> None:
    """available_providers loaded from file or env as list or comma-separated."""
    path = tmp_path / "cfg.json"
    path.write_text(
        '{"ollama_workstation": {"mcp_proxy_url": "http://proxy:3004", '
        '"ollama_base_url": "http://localhost:11434", "ollama_model": "m", '
        '"available_providers": ["ollama", "google"]}}'
    )
    cfg = load_config(str(path))
    assert cfg.available_providers == ("ollama", "google")


def test_config_validation_required() -> None:
    """Missing required fields raise ValueError."""
    from ollama_workstation.commands_policy_config import (
        COMMANDS_POLICY_DENY_BY_DEFAULT,
        CommandsPolicyConfig,
    )

    default_policy = CommandsPolicyConfig(
        allowed_commands=(),
        forbidden_commands=(),
        commands_policy=COMMANDS_POLICY_DENY_BY_DEFAULT,
    )
    with pytest.raises(ValueError, match="mcp_proxy_url"):
        WorkstationConfig(
            mcp_proxy_url="",
            ollama_base_url="http://o:2",
            ollama_model="m",
            commands_policy_config=default_policy,
        )
    with pytest.raises(ValueError, match="ollama_model"):
        WorkstationConfig(
            mcp_proxy_url="http://p:1",
            ollama_base_url="http://o:2",
            ollama_model="",
            commands_policy_config=default_policy,
        )


def test_local_config_example_loads_and_validates() -> None:
    """Local config example (all providers, placeholder keys) loads and validates."""
    root = Path(__file__).resolve().parents[2]
    path = root / "config" / "adapter_config.local.json.example"
    if not path.exists():
        pytest.skip("config/adapter_config.local.json.example not found")
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    errors = validate_project_config(data)
    msg = "local config example should validate: %s" % (errors,)
    assert not errors, msg
    cfg = load_config(str(path))
    assert cfg.mcp_proxy_url
    assert cfg.ollama_model
    assert "ollama" in (cfg.available_providers or ())
    assert cfg.google_api_key
    assert cfg.anthropic_api_key
    assert cfg.openai_api_key
    assert cfg.xai_api_key
    assert cfg.deepseek_api_key
