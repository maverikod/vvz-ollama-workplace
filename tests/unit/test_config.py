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
from mwps.config import (  # noqa: E402
    load_config,
    WorkstationConfig,
    DEFAULT_MAX_TOOL_ROUNDS,
    DEFAULT_MWPS_TIMEOUT,
)
from mwps.docker_config_validation import (  # noqa: E402
    get_runtime_allowed_providers,
    validate_project_config,
)

_PC_MWPS = (
    '"provider_clients": {"default_provider": "mwps", "providers": {"mwps": '
    '{"transport": {"base_url": "http://localhost:11434", "protocol": "http", '
    '"request_timeout_seconds": 120}, "auth": {}, "tls": {}, "features": {}, '
    '"limits": {}}}}'
)


def test_load_config_from_env(tmp_path: Path) -> None:
    """Env overrides config file; defaults for optional."""
    path = tmp_path / "cfg.json"
    path.write_text(
        '{"mwps": {"mcp_proxy_url": "http://x:1", '
        '"mwps": {"base_url": "http://y:2", "model": "z"}}, %s}' % _PC_MWPS
    )
    os.environ["MWPS_MCP_PROXY_URL"] = "http://proxy:3004"
    os.environ["MWPS_BASE_URL"] = "http://mwps:11434"
    os.environ["MWPS_MODEL"] = "qwen3"
    try:
        cfg = load_config(str(path))
        assert cfg.mcp_proxy_url == "http://proxy:3004"
        assert cfg.mwps_base_url == "http://localhost:11434"
        assert cfg.mwps_model == "qwen3"
        assert cfg.max_tool_rounds == DEFAULT_MAX_TOOL_ROUNDS
        assert cfg.mwps_timeout == DEFAULT_MWPS_TIMEOUT
    finally:
        for k in list(os.environ.keys()):
            if k.startswith("MWPS_"):
                del os.environ[k]


def test_load_config_from_json_file() -> None:
    """Load from JSON file with mwps section."""
    data = (
        '{"mwps":{"mcp_proxy_url":"http://p:1",'
        '"mwps":{"base_url":"http://o:2","model":"m"}},%s}' % _PC_MWPS
    )
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        f.write(data.encode())
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg.mcp_proxy_url == "http://p:1"
        assert cfg.mwps_base_url == "http://localhost:11434"
        assert cfg.mwps_model == "m"
    finally:
        Path(path).unlink(missing_ok=True)


def test_load_config_mwps_models() -> None:
    """Config with mwps.models loads and sets mwps_models."""
    data = (
        '{"mwps":{"mcp_proxy_url":"http://p:1",'
        '"mwps":{"base_url":"http://o:2","model":"m",'
        '"models":["llama3.2","qwen3"]}},%s}' % _PC_MWPS
    )
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        f.write(data.encode())
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg.mcp_proxy_url == "http://p:1"
        assert cfg.mwps_model == "m"
        assert cfg.mwps_models == ("llama3.2", "qwen3")
    finally:
        Path(path).unlink(missing_ok=True)


def test_load_config_mwps_timeout() -> None:
    """Config with mwps.timeout loads."""
    data = (
        '{"mwps":{"mcp_proxy_url":"http://p:1",'
        '"mwps":{"base_url":"http://mwps:11434","model":"qwen3",'
        '"models":["qwen3","llama3.2"],"timeout":90}},%s}' % _PC_MWPS
    )
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        f.write(data.encode())
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg.mwps_base_url == "http://localhost:11434"
        assert cfg.mwps_model == "qwen3"
        assert cfg.mwps_models == ("qwen3", "llama3.2")
        assert cfg.mwps_timeout == 90.0
    finally:
        Path(path).unlink(missing_ok=True)


def test_load_config_commands_policy_section() -> None:
    """Config with allowed_commands, forbidden_commands, commands_policy (step 01)."""
    data = (
        '{"mwps":{"mcp_proxy_url":"http://p:1",'
        '"mwps":{"base_url":"http://o:2","model":"m"},'
        '"commands_policy":"deny_by_default",'
        '"allowed_commands":["cmd.server"],"forbidden_commands":[]},%s}' % _PC_MWPS
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
    """Optional mwps.timeout and max_tool_rounds get defaults."""
    path = tmp_path / "cfg.json"
    path.write_text(
        '{"mwps": {"mcp_proxy_url": "http://x:1", '
        '"mwps": {"base_url": "http://y:2", "model": "z"}, '
        '"available_providers": []}, %s}' % _PC_MWPS
    )
    cfg = load_config(str(path))
    assert cfg.mwps_timeout == DEFAULT_MWPS_TIMEOUT
    assert cfg.max_tool_rounds == DEFAULT_MAX_TOOL_ROUNDS


def test_load_config_available_providers(tmp_path: Path) -> None:
    """available_providers loaded from file."""
    path = tmp_path / "cfg.json"
    path.write_text(
        '{"mwps": {"mcp_proxy_url": "http://proxy:3004", '
        '"mwps": {"base_url": "http://localhost:11434", "model": "m"}, '
        '"available_providers": ["mwps", "google"]}, %s}' % _PC_MWPS
    )
    cfg = load_config(str(path))
    assert cfg.available_providers == ("mwps", "google")


def test_config_validation_required() -> None:
    """Missing required fields raise ValueError."""
    from mwps.commands_policy_config import (
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
            mwps_base_url="http://o:2",
            mwps_model="m",
            commands_policy_config=default_policy,
        )
    with pytest.raises(ValueError, match="mwps_model"):
        WorkstationConfig(
            mcp_proxy_url="http://p:1",
            mwps_base_url="http://o:2",
            mwps_model="",
            commands_policy_config=default_policy,
        )


def test_load_config_missing_mwps_section_raises(tmp_path: Path) -> None:
    """Config without mwps.mwps raises."""
    path = tmp_path / "cfg.json"
    path.write_text(
        '{"mwps": {"mcp_proxy_url": "http://p:1"}, %s}' % _PC_MWPS
    )
    with pytest.raises(ValueError, match="mwps.mwps"):
        load_config(str(path))


def test_load_config_missing_provider_clients_raises_no_legacy_fallback(
    tmp_path: Path,
) -> None:
    """Config without provider_clients raises; no autogeneration from legacy."""
    path = tmp_path / "cfg.json"
    path.write_text(
        '{"mwps": {"mcp_proxy_url": "http://p:1", '
        '"mwps": {"base_url": "http://localhost:11434", "model": "m"}, '
        '"model_providers": {"mwps": {"url": "http://localhost:11434"}}}}'
    )
    with pytest.raises(ValueError, match="provider_clients is required"):
        load_config(str(path))


def test_local_config_example_loads_and_validates() -> None:
    """Local config example (provider_clients, placeholder keys) loads and validates."""
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
    assert cfg.mwps_model
    assert cfg.provider_clients_data is not None
    assert "mwps" in (cfg.provider_clients_data.get("providers") or {})
    assert "google" in (cfg.provider_clients_data.get("providers") or {})


def test_validation_runtime_consistency_commercial_has_auth(tmp_path: Path) -> None:
    """
    For config that passes startup validation, resolver must not return
    a commercial endpoint with missing url or api_key (provider_clients only).
    """
    from mwps.model_provider_resolver import (  # noqa: E402
        resolve_model_endpoint_from_provider_clients,
    )

    config_path = tmp_path / "cfg.json"
    app_config = {
        "provider_clients": {
            "default_provider": "mwps",
            "providers": {
                "mwps": {
                    "transport": {
                        "base_url": "http://localhost:11434",
                        "protocol": "http",
                        "request_timeout_seconds": 120,
                    },
                    "auth": {},
                    "tls": {},
                    "features": {},
                    "limits": {},
                },
                "google": {
                    "transport": {
                        "base_url": "https://generativelanguage.googleapis.com/v1beta/",
                        "protocol": "https",
                        "request_timeout_seconds": 120,
                    },
                    "auth": {"api_key": "test-key"},
                    "tls": {"verify": True},
                    "features": {},
                    "limits": {},
                },
            },
        },
        "mwps": {
            "mcp_proxy_url": "http://p:1",
            "mwps": {
                "base_url": "http://localhost:11434",
                "model": "llama3.2",
                "models": ["llama3.2", "gemini-2.0-flash"],
            },
            "available_providers": ["mwps", "google"],
        },
    }
    config_path.write_text(json.dumps(app_config), encoding="utf-8")
    errors = validate_project_config(app_config)
    assert not errors, "valid config must pass validation: %s" % errors
    cfg = load_config(str(config_path))
    runtime_allowed = get_runtime_allowed_providers(app_config)
    assert "google" in runtime_allowed
    endpoint = resolve_model_endpoint_from_provider_clients(
        cfg.provider_clients_data, "gemini-2.0-flash", default_model="llama3.2"
    )
    assert endpoint.base_url
    assert not endpoint.is_mwps
    assert endpoint.api_key, (
        "google is runtime-allowed and config passed validation; "
        "resolver must return endpoint with api_key"
    )
