#!/usr/bin/env python3
"""
Generate adapter config from environment (Docker).
Uses shared config_generator_core; env vars match CLI options.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import os
import sys
import uuid
from pathlib import Path

from ollama_workstation.config_generator_core import generate_adapter_config

MCP_PROXY_HOST = os.environ.get("MCP_PROXY_HOST", "mcp-proxy")
MCP_PROXY_PORT = int(os.environ.get("MCP_PROXY_PORT", "3004"))
CERTS_DIR = os.environ.get("CERTS_DIR", "/app/certs")
CONFIG_PATH = os.environ.get("ADAPTER_CONFIG_PATH", "/app/config/adapter_config.json")
SERVER_PORT = int(os.environ.get("ADAPTER_PORT", "8015"))
INSTANCE_UUID = os.environ.get("REGISTRATION_INSTANCE_UUID") or str(uuid.uuid4())
ADVERTISED_HOST = os.environ.get("ADVERTISED_HOST", "ollama-adapter")
LOG_DIR = os.environ.get("ADAPTER_LOG_DIR", "/app/logs")
_O = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_WORKSTATION_OLLAMA_BASE_URL", _O)
MODEL_SERVER_URL = os.environ.get(
    "OLLAMA_WORKSTATION_MODEL_SERVER_URL", OLLAMA_BASE_URL
)
_DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")
_OLLAMA_PRELOAD_ENV = os.environ.get("OLLAMA_PRELOAD_MODELS", _DEFAULT_MODEL)
OLLAMA_MODELS_LIST = [m.strip() for m in _OLLAMA_PRELOAD_ENV.split(",") if m.strip()]


def main() -> None:
    settings = {
        "output_path": Path(CONFIG_PATH),
        "certs_dir": Path(CERTS_DIR),
        "server_port": SERVER_PORT,
        "mcp_proxy_host": MCP_PROXY_HOST,
        "mcp_proxy_port": MCP_PROXY_PORT,
        "advertised_host": ADVERTISED_HOST,
        "log_dir": LOG_DIR,
        "ollama_base_url": OLLAMA_BASE_URL,
        "model_server_url": MODEL_SERVER_URL,
        "ollama_model": _DEFAULT_MODEL,
        "ollama_models": OLLAMA_MODELS_LIST,
        "redis_password": os.environ.get("OLLAMA_WORKSTATION_REDIS_PASSWORD"),
        "instance_uuid": INSTANCE_UUID,
        "command_execution_timeout_seconds": int(
            os.environ.get("COMMAND_EXECUTION_TIMEOUT_SECONDS", "120")
        ),
        "ollama_timeout": int(
            os.environ.get("OLLAMA_WORKSTATION_OLLAMA_TIMEOUT")
            or os.environ.get("OLLAMA_TIMEOUT", "120")
        ),
        "model_server_container_name": os.environ.get(
            "MODEL_SERVER_CONTAINER_NAME", ""
        ).strip(),
        "model_server_image": os.environ.get("MODEL_SERVER_IMAGE", "").strip(),
    }
    ap_env = (
        os.environ.get("OLLAMA_WORKSTATION_AVAILABLE_PROVIDERS")
        or os.environ.get("AVAILABLE_PROVIDERS", "")
    ).strip()
    if ap_env:
        settings["available_providers"] = [
            p.strip().lower() for p in ap_env.split(",") if p.strip()
        ]
    for env_key, settings_key in (
        ("OLLAMA_WORKSTATION_OLLAMA_API_KEY", "ollama_api_key"),
        ("OLLAMA_WORKSTATION_GOOGLE_API_KEY", "google_api_key"),
        ("OLLAMA_WORKSTATION_ANTHROPIC_API_KEY", "anthropic_api_key"),
        ("OLLAMA_WORKSTATION_OPENAI_API_KEY", "openai_api_key"),
        ("OLLAMA_WORKSTATION_XAI_API_KEY", "xai_api_key"),
        ("OLLAMA_WORKSTATION_DEEPSEEK_API_KEY", "deepseek_api_key"),
        ("OLLAMA_WORKSTATION_OPENROUTER_API_KEY", "openrouter_api_key"),
    ):
        val = os.environ.get(env_key, "").strip()
        if val:
            settings[settings_key] = val
    generate_adapter_config(settings)
    print(f"Wrote {CONFIG_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
