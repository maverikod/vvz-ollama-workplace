"""
Core adapter config generator: build config from a settings dict.
Used by CLI and by docker/container generate_config scripts (env → dict).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import json
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from mcp_proxy_adapter.core.config.simple_config_generator import (
    SimpleConfigGenerator,
)

MODEL_PREFIX_TO_PROVIDER: tuple[tuple[str, str], ...] = (
    ("gemini", "google"),
    ("claude", "anthropic"),
    ("gpt-4", "openai"),
    ("gpt-3.5", "openai"),
    ("gpt-35", "openai"),
    ("o1-", "openai"),
    ("o1-mini", "openai"),
    ("grok", "xai"),
    ("deepseek", "deepseek"),
)

COMMERCIAL_PROVIDER_API_KEY_SETTING: dict[str, str] = {
    "google": "google_api_key",
    "anthropic": "anthropic_api_key",
    "openai": "openai_api_key",
    "xai": "xai_api_key",
    "deepseek": "deepseek_api_key",
    "openrouter": "openrouter_api_key",
}

COMMERCIAL_PROVIDER_DEFAULT_BASE_URL: dict[str, str] = {
    "google": "https://generativelanguage.googleapis.com",
    "anthropic": "https://api.anthropic.com",
    "openai": "https://api.openai.com",
    "xai": "https://api.x.ai",
    "deepseek": "https://api.deepseek.com",
    "openrouter": "https://openrouter.ai/api",
}


def _provider_for_model(model_id: str) -> str:
    mid = (model_id or "").strip().lower()
    for prefix, provider in MODEL_PREFIX_TO_PROVIDER:
        if mid.startswith(prefix):
            return provider
    return "mwps"


def _commercial_providers_from_settings(settings: dict[str, Any]) -> set[str]:
    providers: set[str] = set()
    model_ids = [str(settings.get("mwps_model") or "").strip()]
    for model in settings.get("mwps_models") or []:
        if isinstance(model, str) and model.strip():
            model_ids.append(model.strip())
    for model_id in model_ids:
        provider = _provider_for_model(model_id)
        if provider != "mwps":
            providers.add(provider)
    available = settings.get("available_providers")
    if isinstance(available, str):
        available = [p.strip() for p in available.split(",") if p.strip()]
    if isinstance(available, list):
        for provider in available:
            if isinstance(provider, str):
                provider = provider.strip().lower()
                if provider in COMMERCIAL_PROVIDER_API_KEY_SETTING:
                    providers.add(provider)
    return providers


def generate_adapter_config(settings: dict[str, Any]) -> None:
    """
    Generate adapter config: adapter base (mtls, registration) + project overlay.
    Writes to settings["output_path"].

    Required keys: output_path, certs_dir, server_port, advertised_host, log_dir,
    mwps_base_url, mwps_model, mwps_models (list of str), and either:
    - mcp_proxy_url, or
    - mcp_proxy_host + mcp_proxy_port.
    Optional: redis_password, instance_uuid, registration_server_id,
    mwps_timeout, max_tool_rounds, allowed_commands, forbidden_commands,
    commands_policy, command_discovery_interval_sec, session_store_type,
    redis_host, redis_port, redis_key_prefix, max_context_tokens,
    last_n_messages, min_semantic_tokens, min_documentation_tokens,
    relevance_slot_mode, max_model_call_depth, model_calling_tool_allow_list.
    """
    out_path = str(settings["output_path"])
    certs_dir = Path(settings["certs_dir"])
    server_port = int(settings["server_port"])
    mcp_proxy_url = str(settings.get("mcp_proxy_url", "")).strip().rstrip("/")
    if mcp_proxy_url:
        parsed = urlparse(mcp_proxy_url)
        if not parsed.scheme or not parsed.hostname:
            raise ValueError("Invalid mcp_proxy_url: scheme and hostname are required")
        mcp_host = parsed.hostname
        mcp_port = int(parsed.port or (443 if parsed.scheme == "https" else 80))
        base_url = f"{parsed.scheme}://{mcp_host}:{mcp_port}"
    else:
        mcp_host = str(settings["mcp_proxy_host"])
        mcp_port = int(settings["mcp_proxy_port"])
        base_url = f"https://{mcp_host}:{mcp_port}"
    advertised_host = str(settings["advertised_host"])
    log_dir = str(settings["log_dir"])
    mwps_base_url = str(settings["mwps_base_url"])
    mwps_model = str(settings["mwps_model"])
    mwps_models = list(settings["mwps_models"])

    instance_uuid = settings.get("instance_uuid") or str(uuid.uuid4())
    server_id = settings.get("registration_server_id") or "mwps"

    server_cert = str(certs_dir / "server.crt")
    server_key = str(certs_dir / "server.key")
    ca_crt = str(certs_dir / "ca.crt")
    client_cert = str(certs_dir / "client.crt")
    client_key = str(certs_dir / "client.key")

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    generator = SimpleConfigGenerator()
    generator.generate(
        protocol="mtls",
        with_proxy=True,
        out_path=out_path,
        server_host="0.0.0.0",
        server_port=server_port,
        server_cert_file=server_cert,
        server_key_file=server_key,
        server_ca_cert_file=ca_crt,
        registration_host=mcp_host,
        registration_port=mcp_port,
        registration_protocol="mtls",
        registration_cert_file=client_cert,
        registration_key_file=client_key,
        registration_ca_cert_file=ca_crt,
        registration_server_id=server_id,
        registration_server_name="Model Workplace Server",
        instance_uuid=instance_uuid,
    )

    path = Path(out_path)
    data = json.loads(path.read_text(encoding="utf-8"))

    data.setdefault("server", {})
    data["server"]["servername"] = advertised_host
    data["server"]["advertised_host"] = advertised_host
    data["server"]["log_dir"] = log_dir
    data.setdefault("registration", {})
    data["registration"]["server_id"] = advertised_host
    data["transport"] = {"verify_client": True}

    model_server_url = str(settings.get("model_server_url") or mwps_base_url).strip()
    mwps_timeout = int(settings.get("mwps_timeout", 60))
    container_name = str(settings.get("model_server_container_name", "")).strip()
    container_image = str(settings.get("model_server_image", "")).strip()

    ow_mwps: dict[str, Any] = {
        "base_url": mwps_base_url,
        "model_server_url": model_server_url or mwps_base_url,
        "model": mwps_model,
        "models": mwps_models,
        "timeout": mwps_timeout,
        "container_name": container_name,
        "container_image": container_image,
    }
    ow: dict[str, Any] = {
        "mcp_proxy_url": base_url,
        "mwps": ow_mwps,
        "max_tool_rounds": int(settings.get("max_tool_rounds", 10)),
        "allowed_commands": list(settings.get("allowed_commands", [])),
        "forbidden_commands": list(settings.get("forbidden_commands", [])),
        "commands_policy": str(settings.get("commands_policy", "allow_by_default")),
        "command_discovery_interval_sec": int(
            settings.get("command_discovery_interval_sec", 0)
        ),
        "session_store_type": str(settings.get("session_store_type", "memory")),
        "redis_host": str(settings.get("redis_host", "localhost")),
        "redis_port": int(settings.get("redis_port", 6379)),
        "redis_key_prefix": str(settings.get("redis_key_prefix", "message")),
        "max_context_tokens": int(settings.get("max_context_tokens", 4096)),
        "last_n_messages": int(settings.get("last_n_messages", 10)),
        "min_semantic_tokens": int(settings.get("min_semantic_tokens", 256)),
        "min_documentation_tokens": int(settings.get("min_documentation_tokens", 0)),
        "relevance_slot_mode": str(settings.get("relevance_slot_mode", "fixed_order")),
        "standards_file_path": str(settings.get("standards_file_path", "")).strip(),
        "rules_file_path": str(settings.get("rules_file_path", "")).strip(),
        "max_model_call_depth": int(settings.get("max_model_call_depth", 1)),
        "model_calling_tool_allow_list": list(
            settings.get("model_calling_tool_allow_list", [])
        ),
        "command_execution_timeout_seconds": int(
            settings.get("command_execution_timeout_seconds", 120)
        ),
    }
    ap = settings.get("available_providers")
    if isinstance(ap, list) and ap:
        ow["available_providers"] = [
            str(p).strip().lower() for p in ap if str(p).strip()
        ]
    elif isinstance(ap, str) and ap.strip():
        ow["available_providers"] = [
            p.strip().lower() for p in ap.split(",") if p.strip()
        ]
    if settings.get("redis_password") is not None:
        ow["redis_password"] = str(settings["redis_password"])

    # provider_clients: canonical source for model-workspace; no legacy model_providers.
    mwps_base = (model_server_url or mwps_base_url or "").strip().rstrip("/")
    if not mwps_base:
        mwps_base = "http://127.0.0.1:11434"
    provider_clients: dict[str, Any] = {
        "default_provider": "mwps",
        "providers": {
            "mwps": {
                "transport": {
                    "base_url": mwps_base,
                    "protocol": "https" if mwps_base.startswith("https") else "http",
                    "request_timeout_seconds": mwps_timeout,
                },
                "auth": {},
                "tls": {},
                "features": {},
                "limits": {},
            }
        },
    }
    for provider in sorted(_commercial_providers_from_settings(settings)):
        key_setting = COMMERCIAL_PROVIDER_API_KEY_SETTING[provider]
        api_key = str(settings.get(key_setting) or "").strip()
        if not api_key:
            raise ValueError(
                "Config generation: %s is required for commercial provider %s"
                % (key_setting, provider)
            )
        base_setting = "%s_base_url" % provider
        base_url = str(
            settings.get(base_setting)
            or COMMERCIAL_PROVIDER_DEFAULT_BASE_URL.get(provider, "")
        ).strip()
        provider_clients["providers"][provider] = {
            "transport": {
                "base_url": base_url,
                "protocol": "https" if base_url.startswith("https") else "http",
                "request_timeout_seconds": mwps_timeout,
            },
            "auth": {"api_key": api_key},
            "tls": {"verify": True} if base_url.startswith("https") else {},
            "features": {},
            "limits": {},
        }
    data["provider_clients"] = provider_clients
    data["mwps"] = ow

    from mwps.docker_config_validation import validate_project_config

    errors = validate_project_config(data)
    if errors:
        raise ValueError("Config generation: %s" % errors[0])

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
