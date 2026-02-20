"""
Workstation configuration: load and expose MCP Proxy and OLLAMA settings.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from ollama_workstation.commands_policy_config import (
    COMMANDS_POLICY_ALLOW_BY_DEFAULT,
    COMMANDS_POLICY_VALUES,
    CommandsPolicyConfig,
)

# Default max tool-call rounds per chat (per tech spec)
DEFAULT_MAX_TOOL_ROUNDS = 10
# Default OLLAMA request timeout in seconds
DEFAULT_OLLAMA_TIMEOUT = 60.0

# Environment variable names (single place, no hardcoded URLs in code)
ENV_MCP_PROXY_URL = "OLLAMA_WORKSTATION_MCP_PROXY_URL"
ENV_OLLAMA_BASE_URL = "OLLAMA_WORKSTATION_OLLAMA_BASE_URL"
ENV_OLLAMA_MODEL = "OLLAMA_WORKSTATION_OLLAMA_MODEL"
ENV_OLLAMA_TIMEOUT = "OLLAMA_WORKSTATION_OLLAMA_TIMEOUT"
ENV_MAX_TOOL_ROUNDS = "OLLAMA_WORKSTATION_MAX_TOOL_ROUNDS"


@dataclass
class WorkstationConfig:
    """
    Configuration for the OLLAMA workstation.

    Required: mcp_proxy_url, ollama_base_url, ollama_model.
    Optional: ollama_timeout, max_tool_rounds, and TLS/API key fields if needed.
    """

    mcp_proxy_url: str
    ollama_base_url: str
    ollama_model: str
    ollama_timeout: float = DEFAULT_OLLAMA_TIMEOUT
    max_tool_rounds: int = DEFAULT_MAX_TOOL_ROUNDS
    # Optional: for proxy or OLLAMA auth/TLS (e.g. token, cert paths)
    proxy_token: Optional[str] = None
    proxy_token_header: Optional[str] = None
    ollama_api_key: Optional[str] = None
    # Optional: commands policy (allowed/forbidden/policy); step 01
    commands_policy_config: Optional[CommandsPolicyConfig] = None
    # Optional: command discovery refresh interval in seconds; 0 = startup only (step 03)
    command_discovery_interval_sec: int = 0
    # Optional: session store type e.g. "memory" (step 05)
    session_store_type: str = "memory"
    # Optional: Redis for message stream (step 09): host, port, password, key_prefix
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_key_prefix: str = "message"
    # Context (step 10): max_context_tokens, last_n_messages, min_semantic_tokens, etc.
    max_context_tokens: int = 4096
    last_n_messages: int = 10
    min_semantic_tokens: int = 256
    min_documentation_tokens: int = 0
    relevance_slot_mode: str = "fixed_order"

    def __post_init__(self) -> None:
        """Normalize URLs (strip trailing slash) and validate."""
        self.mcp_proxy_url = (self.mcp_proxy_url or "").rstrip("/")
        self.ollama_base_url = (self.ollama_base_url or "").rstrip("/")
        if not self.mcp_proxy_url:
            raise ValueError("mcp_proxy_url is required")
        if not self.ollama_base_url:
            raise ValueError("ollama_base_url is required")
        if not self.ollama_model:
            raise ValueError("ollama_model is required")
        if self.max_tool_rounds < 1:
            raise ValueError("max_tool_rounds must be >= 1")
        if self.ollama_timeout <= 0:
            raise ValueError("ollama_timeout must be positive")


def _parse_number(value: Any, default: float) -> float:
    """Parse a number from config or env; return default if invalid."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_int(value: Any, default: int) -> int:
    """Parse an integer from config or env; return default if invalid."""
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def load_config(config_path: Optional[str] = None) -> WorkstationConfig:
    """
    Load workstation configuration from a file and/or environment variables.

    Environment variables override file values. Required fields must be set
    either in the file or in the environment.

    Args:
        config_path: Optional path to YAML or JSON config file.

    Returns:
        WorkstationConfig instance.

    Raises:
        ValueError: If required fields are missing after loading.
    """
    data: Dict[str, Any] = {}

    if config_path:
        path = Path(config_path)
        if path.exists():
            raw = path.read_text(encoding="utf-8")
            if path.suffix in (".yaml", ".yml"):
                try:
                    import yaml  # type: ignore[import-untyped]

                    data = yaml.safe_load(raw) or {}
                except ImportError:
                    raise ImportError(
                        "PyYAML is required to load YAML config. "
                        "Install with: pip install PyYAML"
                    ) from None
            else:
                import json

                data = json.loads(raw)

    # Support adapter-style config: values may be under ollama_workstation
    ow: Dict[str, Any] = data.get("ollama_workstation") or {}

    def _get(key: str, default: Any = "") -> Any:
        """Get config value from root or ollama_workstation section."""
        return data.get(key) or ow.get(key, default)

    # Override / fill from environment (env overrides file)
    mcp_proxy_url = os.environ.get(ENV_MCP_PROXY_URL) or _get("mcp_proxy_url", "")
    ollama_base_url = os.environ.get(ENV_OLLAMA_BASE_URL) or _get("ollama_base_url", "")
    ollama_model = os.environ.get(ENV_OLLAMA_MODEL) or _get("ollama_model", "")
    ollama_timeout = _parse_number(
        os.environ.get(ENV_OLLAMA_TIMEOUT) or _get("ollama_timeout"),
        DEFAULT_OLLAMA_TIMEOUT,
    )
    max_tool_rounds = _parse_int(
        os.environ.get(ENV_MAX_TOOL_ROUNDS) or _get("max_tool_rounds"),
        DEFAULT_MAX_TOOL_ROUNDS,
    )
    proxy_token = os.environ.get("OLLAMA_WORKSTATION_PROXY_TOKEN") or _get(
        "proxy_token"
    )
    proxy_token_header = os.environ.get(
        "OLLAMA_WORKSTATION_PROXY_TOKEN_HEADER"
    ) or _get("proxy_token_header")
    ollama_api_key = os.environ.get("OLLAMA_WORKSTATION_OLLAMA_API_KEY") or _get(
        "ollama_api_key"
    )

    commands_policy_config = _load_commands_policy_config(ow)
    cmd_disc_sec = _parse_int(
        os.environ.get("OLLAMA_WORKSTATION_COMMAND_DISCOVERY_INTERVAL_SEC")
        or _get("command_discovery_interval_sec"),
        0,
    )
    command_discovery_interval_sec = max(0, cmd_disc_sec)
    session_store_type = str(_get("session_store_type") or "memory").strip() or "memory"
    redis_host = str(_get("redis_host") or "localhost").strip() or "localhost"
    redis_port = _parse_int(_get("redis_port"), 6379)
    redis_password = _get("redis_password")
    if redis_password is not None:
        redis_password = str(redis_password).strip() or None
    redis_key_prefix = str(_get("redis_key_prefix") or "message").strip() or "message"
    max_context_tokens = max(1, _parse_int(_get("max_context_tokens"), 4096))
    last_n_messages = max(0, _parse_int(_get("last_n_messages"), 10))
    min_semantic_tokens = max(0, _parse_int(_get("min_semantic_tokens"), 256))
    min_documentation_tokens = max(0, _parse_int(_get("min_documentation_tokens"), 0))
    relevance_slot_mode = (
        str(_get("relevance_slot_mode") or "fixed_order").strip() or "fixed_order"
    )

    return WorkstationConfig(
        mcp_proxy_url=mcp_proxy_url,
        ollama_base_url=ollama_base_url,
        ollama_model=ollama_model,
        ollama_timeout=ollama_timeout,
        max_tool_rounds=max_tool_rounds,
        proxy_token=proxy_token,
        proxy_token_header=proxy_token_header,
        ollama_api_key=ollama_api_key,
        commands_policy_config=commands_policy_config,
        command_discovery_interval_sec=command_discovery_interval_sec,
        session_store_type=session_store_type,
        redis_host=redis_host,
        redis_port=redis_port,
        redis_password=redis_password,
        redis_key_prefix=redis_key_prefix,
        max_context_tokens=max_context_tokens,
        last_n_messages=last_n_messages,
        min_semantic_tokens=min_semantic_tokens,
        min_documentation_tokens=min_documentation_tokens,
        relevance_slot_mode=relevance_slot_mode,
    )


def _load_commands_policy_config(ow: Dict[str, Any]) -> Optional[CommandsPolicyConfig]:
    """Build CommandsPolicyConfig from ollama_workstation section if present."""
    allowed = ow.get("allowed_commands")
    forbidden = ow.get("forbidden_commands")
    policy = ow.get("commands_policy")
    if policy is None and allowed is None and forbidden is None:
        return None
    allowed_list: List[str] = list(allowed) if isinstance(allowed, list) else []
    forbidden_list: List[str] = list(forbidden) if isinstance(forbidden, list) else []
    policy_str = (
        str(policy).strip() if policy is not None else COMMANDS_POLICY_ALLOW_BY_DEFAULT
    )
    if policy_str not in COMMANDS_POLICY_VALUES:
        raise ValueError(
            "commands_policy must be one of %s" % (COMMANDS_POLICY_VALUES,)
        )
    return CommandsPolicyConfig(
        allowed_commands=tuple(allowed_list),
        forbidden_commands=tuple(forbidden_list),
        commands_policy=policy_str,
    )
