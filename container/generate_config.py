#!/usr/bin/env python3
"""
Generate adapter config from environment (container).
Uses shared config_generator_core; env vars match CLI options.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import os
import sys
import uuid
from pathlib import Path

from mwps.config_generator_core import generate_adapter_config

MCP_PROXY_URL = os.environ.get("MCP_PROXY_URL", "").strip()
MCP_PROXY_HOST = os.environ.get("MCP_PROXY_HOST", "mcp-proxy")
MCP_PROXY_PORT = int(os.environ.get("MCP_PROXY_PORT", "3004"))
CERTS_DIR = os.environ.get("CERTS_DIR", "/app/certs")
CONFIG_PATH = os.environ.get("ADAPTER_CONFIG_PATH", "/app/config/adapter_config.json")
SERVER_PORT = int(os.environ.get("ADAPTER_PORT", "8443"))
SERVER_ID = os.environ.get("REGISTRATION_SERVER_ID", "mwps")
INSTANCE_UUID = os.environ.get("REGISTRATION_INSTANCE_UUID") or str(uuid.uuid4())
_O = os.environ.get("MWPS_BASE_URL", "http://127.0.0.1:11434")
MWPS_BASE_URL = os.environ.get("MWPS_BASE_URL", _O)
mwps_model = os.environ.get("MWPS_MODEL", "llama3.2")
_preload = os.environ.get("MWPS_PRELOAD_MODELS", mwps_model)
mwps_models_list = [m.strip() for m in _preload.split(",") if m.strip()]


def main() -> None:
    mcp_proxy_url = MCP_PROXY_URL or f"https://{MCP_PROXY_HOST}:{MCP_PROXY_PORT}"
    settings = {
        "output_path": Path(CONFIG_PATH),
        "certs_dir": Path(CERTS_DIR),
        "server_port": SERVER_PORT,
        "mcp_proxy_url": mcp_proxy_url,
        "advertised_host": "mwps",
        "log_dir": "/app/logs",
        "mwps_base_url": MWPS_BASE_URL,
        "mwps_model": mwps_model,
        "mwps_models": mwps_models_list,
        "redis_password": os.environ.get("MWPS_REDIS_PASSWORD"),
        "instance_uuid": INSTANCE_UUID,
        "registration_server_id": SERVER_ID,
    }
    generate_adapter_config(settings)
    print(f"Wrote {CONFIG_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
