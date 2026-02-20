#!/usr/bin/env python3
"""
Generate adapter config: use mcp_proxy_adapter SimpleConfigGenerator for base
config, then apply project-specific overrides (transport, log_dir, advertised
host, ollama_workstation). Same approach as validation: adapter first, our
settings on top.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import json
import os
import sys
import uuid
from pathlib import Path

from mcp_proxy_adapter.core.config.simple_config_generator import (
    SimpleConfigGenerator,
)

# --- Env used by generator (paths, ports, proxy) ---
MCP_PROXY_HOST = os.environ.get("MCP_PROXY_HOST", "mcp-proxy")
MCP_PROXY_PORT = int(os.environ.get("MCP_PROXY_PORT", "3004"))
CERTS_DIR = os.environ.get("CERTS_DIR", "/app/certs")
CONFIG_PATH = os.environ.get("ADAPTER_CONFIG_PATH", "/app/config/adapter_config.json")
SERVER_PORT = int(os.environ.get("ADAPTER_PORT", "8015"))
INSTANCE_UUID = os.environ.get("REGISTRATION_INSTANCE_UUID") or str(uuid.uuid4())

# --- Our overrides (applied after generator) ---
ADVERTISED_HOST = os.environ.get("ADVERTISED_HOST", "ollama-adapter")
LOG_DIR = os.environ.get("ADAPTER_LOG_DIR", "/app/logs")
# In Docker use host.docker.internal:11434 or service name (e.g. ollama:11434)
_O = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_WORKSTATION_OLLAMA_BASE_URL", _O)
# Model names to preload (OLLAMA_MODELS is path in Docker)
_DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")
_OLLAMA_PRELOAD_ENV = os.environ.get("OLLAMA_PRELOAD_MODELS", _DEFAULT_MODEL)
OLLAMA_MODELS_LIST = [m.strip() for m in _OLLAMA_PRELOAD_ENV.split(",") if m.strip()]


def main() -> None:
    server_cert = str(Path(CERTS_DIR) / "server.crt")
    server_key = str(Path(CERTS_DIR) / "server.key")
    ca_crt = str(Path(CERTS_DIR) / "ca.crt")
    client_cert = str(Path(CERTS_DIR) / "client.crt")
    client_key = str(Path(CERTS_DIR) / "client.key")

    # 1. Base config from adapter generator (use its default server_id/name)
    generator = SimpleConfigGenerator()
    generator.generate(
        protocol="mtls",
        with_proxy=True,
        out_path=CONFIG_PATH,
        server_host="0.0.0.0",
        server_port=SERVER_PORT,
        server_cert_file=server_cert,
        server_key_file=server_key,
        server_ca_cert_file=ca_crt,
        registration_host=MCP_PROXY_HOST,
        registration_port=MCP_PROXY_PORT,
        registration_protocol="mtls",
        registration_cert_file=client_cert,
        registration_key_file=client_key,
        registration_ca_cert_file=ca_crt,
        registration_server_id="ollama-workstation",
        registration_server_name="OLLAMA Workstation",
        instance_uuid=INSTANCE_UUID,
    )

    # 2. Apply only our project settings on top of generated config
    path = Path(CONFIG_PATH)
    data = json.loads(path.read_text(encoding="utf-8"))

    data.setdefault("server", {})
    data["server"]["servername"] = ADVERTISED_HOST
    data["server"]["advertised_host"] = ADVERTISED_HOST
    data["server"]["log_dir"] = LOG_DIR

    data.setdefault("registration", {})
    data["registration"]["server_id"] = ADVERTISED_HOST

    data["transport"] = {"verify_client": True}

    base_url = f"https://{MCP_PROXY_HOST}:{MCP_PROXY_PORT}"
    data["ollama_workstation"] = {
        "mcp_proxy_url": base_url,
        "ollama_base_url": OLLAMA_BASE_URL,
        "ollama_model": os.environ.get("OLLAMA_MODEL", "llama3.2"),
        "ollama_models": OLLAMA_MODELS_LIST,
        "ollama_timeout": 60,
        "max_tool_rounds": 10,
        "allowed_commands": [],
        "forbidden_commands": [],
        "commands_policy": "allow_by_default",
        "command_discovery_interval_sec": 0,
        "session_store_type": "memory",
    }

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {CONFIG_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
