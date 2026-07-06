"""
Workstation configuration: load and expose MCP Proxy and MWPS settings.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from mwps.commands_policy_config import (
    COMMANDS_POLICY_ALLOW_BY_DEFAULT,
    COMMANDS_POLICY_DENY_BY_DEFAULT,
    COMMANDS_POLICY_VALUES,
    CommandsPolicyConfig,
)
from mwps.provider_client_config_validator import (
    validate_provider_clients_or_raise,
)

# Default max tool-call rounds per chat (per tech spec)
DEFAULT_MAX_TOOL_ROUNDS = 10
# Default MWPS request timeout in seconds
DEFAULT_MWPS_TIMEOUT = 60.0

# Environment variable names (single place, no hardcoded URLs in code)
ENV_MCP_PROXY_URL = "MWPS_MCP_PROXY_URL"
ENV_MWPS_BASE_URL = "MWPS_BASE_URL"
ENV_MODEL_SERVER_URL = "MWPS_MODEL_SERVER_URL"
ENV_MWPS_MODEL = "MWPS_MODEL"
ENV_MWPS_TIMEOUT = "MWPS_TIMEOUT"
ENV_MAX_TOOL_ROUNDS = "MWPS_MAX_TOOL_ROUNDS"


@dataclass
class WorkstationConfig:
    """
    Configuration for the Agent Workstation.

    Required: mcp_proxy_url, mwps_base_url, mwps_model.
    Optional: mwps_timeout, max_tool_rounds, and TLS/API key fields if needed.
    """

    mcp_proxy_url: str
    mwps_base_url: str
    mwps_model: str
    # Model server URL (Model Workplace Server or other backend).
    # If empty, equals mwps_base_url.
    model_server_url: str = ""
    mwps_timeout: float = DEFAULT_MWPS_TIMEOUT
    # Optional list of model ids (e.g. for representation registry).
    mwps_models: Tuple[str, ...] = ()
    max_tool_rounds: int = DEFAULT_MAX_TOOL_ROUNDS
    # Optional: for proxy or MWPS auth/TLS (e.g. token, cert paths)
    proxy_token: Optional[str] = None
    proxy_token_header: Optional[str] = None
    # Proxy client mTLS (from registration.ssl when using registration section)
    proxy_client_cert: Optional[str] = None
    proxy_client_key: Optional[str] = None
    proxy_ca_cert: Optional[str] = None
    mwps_api_key: Optional[str] = None
    # Commands policy: model context only from config allowed list, then session filter.
    # Default: deny_by_default with empty allowed (no tools until config lists them).
    commands_policy_config: CommandsPolicyConfig = field(
        default_factory=lambda: CommandsPolicyConfig(
            allowed_commands=(),
            forbidden_commands=(),
            commands_policy=COMMANDS_POLICY_DENY_BY_DEFAULT,
        )
    )
    # Optional: command discovery interval (sec); 0 = startup only (step 03)
    command_discovery_interval_sec: int = 0
    # Optional: session store type e.g. "memory" (step 05)
    session_store_type: str = "memory"
    # Optional: Redis for message stream (step 09): host, port, password, key_prefix
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_key_prefix: str = "message"
    # Context (step 10): max_context_tokens, last_n_messages, etc.
    max_context_tokens: int = 4096
    last_n_messages: int = 10
    min_documentation_tokens: int = 0
    # Step 12: tool→model recursion
    max_model_call_depth: int = 1
    model_calling_tool_allow_list: tuple[str, ...] = ()
    # Optional: paths to files auto-injected into context when present
    rules_file_path: str = ""
    standards_file_path: str = ""
    tools_file_path: str = ""
    # Optional: this adapter's server_id (priority when deduping by name).
    adapter_server_id: str = ""
    # Adapter command execution timeout (sec). When chat exceeds it we return
    # ErrorResult with message instead of raising so the client gets a clear error.
    command_execution_timeout_seconds: int = 120
    # Normalized provider_clients section (validated at load). Used by chat_flow
    # to obtain provider client via registry; invalid config blocks startup.
    provider_clients_data: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        """Normalize URLs (strip trailing slash) and validate."""
        self.mcp_proxy_url = (self.mcp_proxy_url or "").rstrip("/")
        self.mwps_base_url = (self.mwps_base_url or "").rstrip("/")
        self.model_server_url = (self.model_server_url or "").rstrip("/")
        if not self.model_server_url:
            self.model_server_url = self.mwps_base_url
        if not self.mcp_proxy_url:
            raise ValueError("mcp_proxy_url is required")
        if not self.mwps_base_url:
            raise ValueError("mwps_base_url is required")
        if not self.model_server_url:
            raise ValueError("model_server_url or mwps_base_url is required")
        if not self.mwps_model:
            raise ValueError("mwps_model is required")
        if self.max_tool_rounds < 1:
            raise ValueError("max_tool_rounds must be >= 1")
        if self.mwps_timeout <= 0:
            raise ValueError("mwps_timeout must be positive")


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


def _proxy_from_registration(
    registration: Dict[str, Any],
) -> Tuple[str, str, int, Optional[str], Optional[str], Optional[str]]:
    """
    Derive proxy protocol, host, port and client TLS paths from registration.

    Uses register_url (or heartbeat.url) for scheme/host/port; registration.ssl
    for cert, key, ca. Returns (protocol, host, port, cert_path, key_path, ca_path).
    """
    url_str = (
        registration.get("register_url")
        or registration.get("heartbeat", {}).get("url")
        or ""
    )
    if not url_str:
        return ("https", "localhost", 443, None, None, None)
    parsed = urlparse(url_str)
    scheme = (parsed.scheme or "https").lower()
    protocol = "https" if scheme == "https" else "http"
    host = parsed.hostname or "localhost"
    port = parsed.port
    if port is None:
        port = 443 if scheme == "https" else 80
    ssl_cfg = registration.get("ssl") or {}
    cert = ssl_cfg.get("cert")
    key = ssl_cfg.get("key")
    ca = ssl_cfg.get("ca")
    cert_path = str(cert).strip() if cert else None
    key_path = str(key).strip() if key else None
    ca_path = str(ca).strip() if ca else None
    return (protocol, host, port, cert_path or None, key_path or None, ca_path or None)


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
                    import yaml

                    data = yaml.safe_load(raw) or {}
                except ImportError:
                    raise ImportError(
                        "PyYAML is required to load YAML config. "
                        "Install with: pip install PyYAML"
                    ) from None
            else:
                import json

                data = json.loads(raw)

    # Support adapter-style config: values may be under mwps
    ow: Dict[str, Any] = data.get("mwps") or {}

    def _get(key: str, default: Any = "") -> Any:
        """Get config value from root or mwps section."""
        return data.get(key) or ow.get(key, default)

    # Proxy URL: from registration section (protocol, host, port) or mwps
    registration = data.get("registration") or {}
    if registration and not os.environ.get(ENV_MCP_PROXY_URL):
        proto, host, port, cert_p, key_p, ca_p = _proxy_from_registration(registration)
        mcp_proxy_url = "%s://%s:%s" % (proto, host, port)
        proxy_client_cert = cert_p
        proxy_client_key = key_p
        proxy_ca_cert = ca_p
    else:
        mcp_proxy_url = os.environ.get(ENV_MCP_PROXY_URL) or _get("mcp_proxy_url", "")
        proxy_client_cert = _get("proxy_client_cert") or None
        proxy_client_key = _get("proxy_client_key") or None
        proxy_ca_cert = _get("proxy_ca_cert") or None
        if proxy_client_cert is not None:
            proxy_client_cert = str(proxy_client_cert).strip() or None
        if proxy_client_key is not None:
            proxy_client_key = str(proxy_client_key).strip() or None
        if proxy_ca_cert is not None:
            proxy_ca_cert = str(proxy_ca_cert).strip() or None
    mwps_section = ow.get("mwps")
    if not isinstance(mwps_section, dict):
        raise ValueError("mwps.mwps is required and must be an object")
    o = mwps_section

    mwps_base_url = (
        os.environ.get(ENV_MWPS_BASE_URL) or (o.get("base_url") or "").strip()
    )
    model_server_url = (
        os.environ.get(ENV_MODEL_SERVER_URL)
        or (o.get("model_server_url") or o.get("base_url") or "").strip()
    )
    if not model_server_url:
        model_server_url = mwps_base_url
    mwps_model = os.environ.get(ENV_MWPS_MODEL) or (o.get("model") or "").strip()
    mwps_timeout = _parse_number(
        os.environ.get(ENV_MWPS_TIMEOUT) or o.get("timeout"),
        DEFAULT_MWPS_TIMEOUT,
    )
    _mwps_models_raw = o.get("models")
    if isinstance(_mwps_models_raw, list):
        mwps_models = tuple(str(m).strip() for m in _mwps_models_raw if str(m).strip())
    else:
        mwps_models = ()
    max_tool_rounds = _parse_int(
        os.environ.get(ENV_MAX_TOOL_ROUNDS) or _get("max_tool_rounds"),
        DEFAULT_MAX_TOOL_ROUNDS,
    )
    proxy_token = os.environ.get("MWPS_PROXY_TOKEN") or _get("proxy_token")
    proxy_token_header = os.environ.get("MWPS_PROXY_TOKEN_HEADER") or _get(
        "proxy_token_header"
    )

    # Legacy provider fields are not read for provider routing (model-workspace
    # uses only provider_clients). No fallback; empty so runtime never uses legacy.
    mwps_api_key: Optional[str] = None

    commands_policy_config = _load_commands_policy_config(ow)
    cmd_disc_sec = _parse_int(
        os.environ.get("MWPS_COMMAND_DISCOVERY_INTERVAL_SEC")
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
    min_documentation_tokens = max(0, _parse_int(_get("min_documentation_tokens"), 0))
    max_model_call_depth = max(0, _parse_int(_get("max_model_call_depth"), 1))
    allow_list_raw = ow.get("model_calling_tool_allow_list")
    if isinstance(allow_list_raw, list):
        model_calling_tool_allow_list = tuple(
            str(x).strip() for x in allow_list_raw if str(x).strip()
        )
    else:
        model_calling_tool_allow_list = ()
    rules_file_path = str(_get("rules_file_path") or "").strip()
    standards_file_path = str(_get("standards_file_path") or "").strip()
    tools_file_path = str(_get("tools_file_path") or "").strip()
    adapter_server_id = str(
        _get("adapter_server_id") or data.get("server", {}).get("advertised_host") or ""
    ).strip()
    command_execution_timeout_seconds = max(
        30,
        _parse_int(_get("command_execution_timeout_seconds"), 120),
    )

    # Provider clients: required from config; no autogeneration from legacy fields.
    provider_clients_raw = data.get("provider_clients") or ow.get("provider_clients")
    if not isinstance(provider_clients_raw, dict):
        raise ValueError(
            "provider_clients is required; no autogeneration from legacy fields. "
            "Add provider_clients.default_provider and provider_clients.providers."
        )
    provider_clients_data = dict(provider_clients_raw)
    validate_provider_clients_or_raise(provider_clients_data)
    # Canonical source for mwps URL when default provider is mwps.
    default_provider = (
        (provider_clients_data.get("default_provider") or "").strip().lower()
    )
    providers_dict = provider_clients_data.get("providers") or {}
    if default_provider == "mwps" and isinstance(providers_dict.get("mwps"), dict):
        otr = providers_dict["mwps"].get("transport") or {}
        base = (otr.get("base_url") or "").strip().rstrip("/")
        if base:
            mwps_base_url = base
            model_server_url = base

    return WorkstationConfig(
        mcp_proxy_url=mcp_proxy_url,
        mwps_base_url=mwps_base_url,
        mwps_model=mwps_model,
        mwps_models=mwps_models,
        model_server_url=model_server_url,
        mwps_timeout=mwps_timeout,
        max_tool_rounds=max_tool_rounds,
        proxy_token=proxy_token,
        proxy_token_header=proxy_token_header,
        proxy_client_cert=proxy_client_cert,
        proxy_client_key=proxy_client_key,
        proxy_ca_cert=proxy_ca_cert,
        mwps_api_key=mwps_api_key,
        commands_policy_config=commands_policy_config,
        command_discovery_interval_sec=command_discovery_interval_sec,
        session_store_type=session_store_type,
        redis_host=redis_host,
        redis_port=redis_port,
        redis_password=redis_password,
        redis_key_prefix=redis_key_prefix,
        max_context_tokens=max_context_tokens,
        last_n_messages=last_n_messages,
        min_documentation_tokens=min_documentation_tokens,
        max_model_call_depth=max_model_call_depth,
        model_calling_tool_allow_list=model_calling_tool_allow_list,
        rules_file_path=rules_file_path,
        standards_file_path=standards_file_path,
        tools_file_path=tools_file_path,
        adapter_server_id=adapter_server_id,
        command_execution_timeout_seconds=command_execution_timeout_seconds,
        provider_clients_data=provider_clients_data,
    )


def _load_commands_policy_config(ow: Dict[str, Any]) -> CommandsPolicyConfig:
    """
    Build CommandsPolicyConfig from mwps section.
    Model context: only commands specified in config, then filtered by session.
    When allowed_commands/forbidden_commands/commands_policy are absent, defaults to
    deny_by_default with empty allowed (no tools until config lists allowed_commands).
    """
    allowed = ow.get("allowed_commands")
    forbidden = ow.get("forbidden_commands")
    policy = ow.get("commands_policy")
    allowed_list: List[str] = list(allowed) if isinstance(allowed, list) else []
    forbidden_list: List[str] = list(forbidden) if isinstance(forbidden, list) else []
    if policy is None and allowed is None and forbidden is None:
        policy_str = COMMANDS_POLICY_DENY_BY_DEFAULT
    else:
        policy_str = (
            str(policy).strip()
            if policy is not None
            else COMMANDS_POLICY_ALLOW_BY_DEFAULT
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
