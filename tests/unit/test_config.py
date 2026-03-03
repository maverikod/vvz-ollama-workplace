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
    get_runtime_allowed_providers,
    validate_project_config,
)
from ollama_workstation.model_provider_resolver import (  # noqa: E402
    resolve_model_endpoint,
)


def test_load_config_from_env(tmp_path: Path) -> None:
    """Env overrides config file; defaults for optional."""
    path = tmp_path / "cfg.json"
    path.write_text(
        '{"ollama_workstation": {"mcp_proxy_url": "http://x:1", '
        '"ollama": {"base_url": "http://y:2", "model": "z"}}}'
    )
    os.environ["OLLAMA_WORKSTATION_MCP_PROXY_URL"] = "http://proxy:3004"
    os.environ["OLLAMA_WORKSTATION_OLLAMA_BASE_URL"] = "http://ollama:11434"
    os.environ["OLLAMA_WORKSTATION_OLLAMA_MODEL"] = "qwen3"
    try:
        cfg = load_config(str(path))
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
    """Load from JSON file with ollama section."""
    data = (
        '{"ollama_workstation":{"mcp_proxy_url":"http://p:1",'
        '"ollama":{"base_url":"http://o:2","model":"m"}}}'
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


def test_load_config_ollama_models() -> None:
    """Config with ollama.models loads and sets ollama_models."""
    data = (
        '{"ollama_workstation":{"mcp_proxy_url":"http://p:1",'
        '"ollama":{"base_url":"http://o:2","model":"m",'
        '"models":["llama3.2","qwen3"]}}}'
    )
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        f.write(data.encode())
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg.mcp_proxy_url == "http://p:1"
        assert cfg.ollama_model == "m"
        assert cfg.ollama_models == ("llama3.2", "qwen3")
    finally:
        Path(path).unlink(missing_ok=True)


def test_load_config_ollama_timeout() -> None:
    """Config with ollama.timeout loads."""
    data = (
        '{"ollama_workstation":{"mcp_proxy_url":"http://p:1",'
        '"ollama":{"base_url":"http://ollama:11434","model":"qwen3",'
        '"models":["qwen3","llama3.2"],"timeout":90}}}'
    )
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        f.write(data.encode())
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg.ollama_base_url == "http://ollama:11434"
        assert cfg.ollama_model == "qwen3"
        assert cfg.ollama_models == ("qwen3", "llama3.2")
        assert cfg.ollama_timeout == 90.0
    finally:
        Path(path).unlink(missing_ok=True)


def test_load_config_commands_policy_section() -> None:
    """Config with allowed_commands, forbidden_commands, commands_policy (step 01)."""
    data = (
        '{"ollama_workstation":{"mcp_proxy_url":"http://p:1",'
        '"ollama":{"base_url":"http://o:2","model":"m"},'
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


def test_load_config_optional_fields_and_defaults(tmp_path: Path) -> None:
    """Optional ollama.timeout and max_tool_rounds get defaults."""
    path = tmp_path / "cfg.json"
    path.write_text(
        '{"ollama_workstation": {"mcp_proxy_url": "http://x:1", '
        '"ollama": {"base_url": "http://y:2", "model": "z"}, '
        '"available_providers": []}}'
    )
    cfg = load_config(str(path))
    assert cfg.ollama_timeout == DEFAULT_OLLAMA_TIMEOUT
    assert cfg.max_tool_rounds == DEFAULT_MAX_TOOL_ROUNDS


def test_load_config_available_providers(tmp_path: Path) -> None:
    """available_providers loaded from file."""
    path = tmp_path / "cfg.json"
    path.write_text(
        '{"ollama_workstation": {"mcp_proxy_url": "http://proxy:3004", '
        '"ollama": {"base_url": "http://localhost:11434", "model": "m"}, '
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


def test_load_config_missing_ollama_section_raises(tmp_path: Path) -> None:
    """Config without ollama_workstation.ollama raises."""
    path = tmp_path / "cfg.json"
    path.write_text('{"ollama_workstation": {"mcp_proxy_url": "http://p:1"}}')
    with pytest.raises(ValueError, match="ollama_workstation.ollama"):
        load_config(str(path))


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
    assert cfg.model_providers.get("google", {}).get("api_key")
    assert cfg.model_providers.get("anthropic", {}).get("api_key")
    assert cfg.model_providers.get("openai", {}).get("api_key")


def test_validation_runtime_consistency_commercial_has_auth(tmp_path: Path) -> None:
    """
    For config that passes startup validation, resolver must not return
    a commercial endpoint with missing url or api_key (consistency).
    """
    config_path = tmp_path / "cfg.json"
    app_config = {
        "ollama_workstation": {
            "mcp_proxy_url": "http://p:1",
            "ollama": {
                "base_url": "http://localhost:11434",
                "model": "llama3.2",
                "models": ["llama3.2", "gemini-2.0-flash"],
            },
            "available_providers": ["ollama", "google"],
            "model_providers": {
                "ollama": {"url": "http://localhost:11434"},
                "google": {
                    "url": "https://generativelanguage.googleapis.com/v1beta/",
                    "api_key": "test-key",
                },
            },
        },
    }
    config_path.write_text(json.dumps(app_config), encoding="utf-8")
    errors = validate_project_config(app_config)
    assert not errors, "valid config must pass validation: %s" % errors
    cfg = load_config(str(config_path))
    runtime_allowed = get_runtime_allowed_providers(app_config)
    # One commercial in runtime_allowed: google; model gemini-2.0-flash maps to it.
    endpoint = resolve_model_endpoint("gemini-2.0-flash", cfg)
    assert "google" in runtime_allowed
    assert endpoint.base_url
    assert not endpoint.is_ollama
    assert endpoint.api_key, (
        "google is runtime-allowed and config passed validation; "
        "resolver must return endpoint with api_key"
    )
