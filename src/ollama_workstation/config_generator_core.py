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

from mcp_proxy_adapter.core.config.simple_config_generator import (
    SimpleConfigGenerator,
)

from ollama_workstation.docker_config_validation import (
    validate_model_providers,
)


def generate_adapter_config(settings: dict[str, Any]) -> None:
    """
    Generate adapter config: adapter base (mtls, registration) + project overlay.
    Writes to settings["output_path"].

    Required keys: output_path, certs_dir, server_port, mcp_proxy_host,
    mcp_proxy_port, advertised_host, log_dir, ollama_base_url, ollama_model,
    ollama_models (list of str).
    Optional: redis_password, instance_uuid, registration_server_id,
    ollama_timeout, max_tool_rounds, allowed_commands, forbidden_commands,
    commands_policy, command_discovery_interval_sec, session_store_type,
    redis_host, redis_port, redis_key_prefix, max_context_tokens,
    last_n_messages, min_semantic_tokens, min_documentation_tokens,
    relevance_slot_mode, max_model_call_depth, model_calling_tool_allow_list.
    """
    out_path = str(settings["output_path"])
    certs_dir = Path(settings["certs_dir"])
    server_port = int(settings["server_port"])
    mcp_host = str(settings["mcp_proxy_host"])
    mcp_port = int(settings["mcp_proxy_port"])
    advertised_host = str(settings["advertised_host"])
    log_dir = str(settings["log_dir"])
    ollama_base_url = str(settings["ollama_base_url"])
    ollama_model = str(settings["ollama_model"])
    ollama_models = list(settings["ollama_models"])

    instance_uuid = settings.get("instance_uuid") or str(uuid.uuid4())
    server_id = settings.get("registration_server_id") or "ollama-workstation"

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
        registration_server_name="OLLAMA Workstation",
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

    base_url = f"https://{mcp_host}:{mcp_port}"
    model_server_url = str(settings.get("model_server_url") or ollama_base_url).strip()
    ow: dict[str, Any] = {
        "mcp_proxy_url": base_url,
        "ollama_base_url": ollama_base_url,
        "model_server_url": model_server_url or ollama_base_url,
        "ollama_model": ollama_model,
        "ollama_models": ollama_models,
        "ollama_timeout": int(settings.get("ollama_timeout", 60)),
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
        "max_model_call_depth": int(settings.get("max_model_call_depth", 1)),
        "model_calling_tool_allow_list": list(
            settings.get("model_calling_tool_allow_list", [])
        ),
        "command_execution_timeout_seconds": int(
            settings.get("command_execution_timeout_seconds", 120)
        ),
        "model_server_container_name": str(
            settings.get("model_server_container_name", "")
        ).strip(),
        "model_server_image": str(settings.get("model_server_image", "")).strip(),
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

    # model_providers: url and api_key per provider (mandatory when model selected).
    model_providers: dict[str, dict[str, str]] = {}
    default_urls = {
        "ollama": model_server_url or ollama_base_url,
        "google": "https://generativelanguage.googleapis.com/v1beta",
        "anthropic": "https://api.anthropic.com/v1",
        "openai": "https://api.openai.com/v1",
        "xai": "https://api.x.ai/v1",
        "deepseek": "https://api.deepseek.com/v1",
        "openrouter": "https://openrouter.ai/api/v1",
    }
    prov_urls = settings.get("provider_urls")
    if isinstance(prov_urls, dict):
        for prov, v in prov_urls.items():
            if (
                isinstance(prov, str)
                and prov.strip()
                and isinstance(v, str)
                and v.strip()
            ):
                model_providers[prov.strip().lower()] = {"url": v.strip().rstrip("/")}
    mp_raw = settings.get("model_providers")
    if isinstance(mp_raw, dict):
        for prov, cfg in mp_raw.items():
            if isinstance(prov, str) and prov.strip() and isinstance(cfg, dict):
                p = prov.strip().lower()
                u = (cfg.get("url") or "").strip().rstrip("/") or default_urls.get(
                    p, ""
                )
                k = (cfg.get("api_key") or "").strip()
                model_providers[p] = {}
                if u:
                    model_providers[p]["url"] = u
                if k:
                    model_providers[p]["api_key"] = k
    for key, prov in (
        ("ollama_api_key", "ollama"),
        ("google_api_key", "google"),
        ("anthropic_api_key", "anthropic"),
        ("openai_api_key", "openai"),
        ("xai_api_key", "xai"),
        ("deepseek_api_key", "deepseek"),
        ("openrouter_api_key", "openrouter"),
    ):
        val = settings.get(key)
        if val is not None and str(val).strip():
            if prov not in model_providers:
                model_providers[prov] = {}
            model_providers[prov]["api_key"] = str(val).strip()
            if "url" not in model_providers[prov]:
                model_providers[prov]["url"] = default_urls.get(prov, "")
    if "ollama" not in model_providers and (model_server_url or ollama_base_url):
        model_providers["ollama"] = {"url": model_server_url or ollama_base_url}
    if model_providers:
        ow["model_providers"] = model_providers
    for key in (
        "ollama_api_key",
        "google_api_key",
        "anthropic_api_key",
        "openai_api_key",
        "xai_api_key",
        "deepseek_api_key",
        "openrouter_api_key",
    ):
        val = settings.get(key)
        if val is not None and str(val).strip():
            ow[key] = str(val).strip()
    data["ollama_workstation"] = ow

    # When model selected: url and api_key for its provider are mandatory.
    prov_errors = validate_model_providers(ow, ollama_model, ollama_models)
    if prov_errors:
        raise ValueError("Config generation: %s" % prov_errors[0])

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
