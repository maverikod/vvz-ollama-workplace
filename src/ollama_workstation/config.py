"""
Workstation configuration: load and expose MCP Proxy and OLLAMA settings.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

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

    # Override / fill from environment
    mcp_proxy_url = os.environ.get(ENV_MCP_PROXY_URL) or data.get("mcp_proxy_url", "")
    ollama_base_url = os.environ.get(ENV_OLLAMA_BASE_URL) or data.get(
        "ollama_base_url", ""
    )
    ollama_model = os.environ.get(ENV_OLLAMA_MODEL) or data.get("ollama_model", "")
    ollama_timeout = _parse_number(
        os.environ.get(ENV_OLLAMA_TIMEOUT) or data.get("ollama_timeout"),
        DEFAULT_OLLAMA_TIMEOUT,
    )
    max_tool_rounds = _parse_int(
        os.environ.get(ENV_MAX_TOOL_ROUNDS) or data.get("max_tool_rounds"),
        DEFAULT_MAX_TOOL_ROUNDS,
    )
    proxy_token = os.environ.get("OLLAMA_WORKSTATION_PROXY_TOKEN") or data.get(
        "proxy_token"
    )
    proxy_token_header = os.environ.get(
        "OLLAMA_WORKSTATION_PROXY_TOKEN_HEADER"
    ) or data.get("proxy_token_header")
    ollama_api_key = os.environ.get("OLLAMA_WORKSTATION_OLLAMA_API_KEY") or data.get(
        "ollama_api_key"
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
    )
