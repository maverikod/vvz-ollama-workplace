#!/usr/bin/env python3
"""
Run MCP Proxy Adapter with MWPS: load config, register command, start server.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from mcp_proxy_adapter.api.app import create_app
from mcp_proxy_adapter.config import get_config
from mcp_proxy_adapter.core.app_factory.ssl_config import (
    build_server_ssl_config,
)
from mcp_proxy_adapter.core.config.simple_config import SimpleConfig
from mcp_proxy_adapter.core.server_engine import ServerEngineFactory
from mcp_proxy_adapter.commands.command_registry import (
    registry,
)

from mwps.docker_config_validation import validate_project_config

# So that chat_flow, mwps_chat_command, proxy_client INFO appear in adapter logs.
logging.getLogger("mwps").setLevel(logging.INFO)

# Server description for proxy catalog.
MWPS_SERVER_DESCRIPTION = (
    "Model Workplace Server: MCP adapter that runs chat via a configured provider "
    "client and gives the model access to MCP Proxy tools (list_servers, "
    "call_server, help). Use mwps_chat to send messages and get replies; model "
    "can call any server. Session commands (session_init, session_update, "
    "add_command_to_session, remove_command_from_session) manage per-session "
    "allow/forbid lists."
)

DATABASE_SERVER_DESCRIPTION = (
    "Database Server: MCP adapter exposing Redis domain API. Commands: "
    "message_write, messages_get_by_session, session_get, session_create, "
    "session_update. Full command catalog with strict JSON Schema; mTLS."
)


def register_commands() -> None:
    """Register commands by server_id: workstation | database-server."""
    cfg = get_config()
    cfg_data = getattr(cfg, "config_data", None) or {}
    server_id = str((cfg_data.get("registration") or {}).get("server_id") or "").strip()
    if server_id == "database-server":
        from database_server.commands import register_database_commands

        register_database_commands(registry)
    else:
        from mwps.registration import register_mwps

        register_mwps(registry)


def main() -> int:
    """Load config, validate, create app, register commands, run hypercorn."""
    parser = argparse.ArgumentParser(description="MWPS + MCP Adapter (mTLS)")
    parser.add_argument(
        "--config",
        default="/app/config/adapter_config.json",
        help="Path to adapter JSON config",
    )
    args = parser.parse_args()

    cfg_path = Path(args.config)
    if not cfg_path.exists():
        print(f"Config not found: {cfg_path}", file=sys.stderr)
        return 1

    with open(cfg_path, encoding="utf-8") as f:
        app_config = json.load(f)

    simple_config = SimpleConfig(str(cfg_path))
    model = simple_config.load()

    # 1. Adapter validation first
    errors = [getattr(e, "message", str(e)) for e in simple_config.validate()]

    # 2. Project-specific validation by server role
    reg = app_config.get("registration") or {}
    server_id = str(reg.get("server_id") or "").strip()
    if server_id == "database-server":
        from database_server.config_validator import validate_database_server_config

        errors.extend(validate_database_server_config(app_config))
    else:
        errors.extend(validate_project_config(app_config))

    if errors:
        for msg in errors:
            print(f"Validation: {msg}", file=sys.stderr)
        return 1

    simple_config.model = model
    for section, value in simple_config.to_dict().items():
        app_config[section] = value

    app_config.setdefault("server", {})
    app_config["server"].setdefault("debug", False)
    app_config["server"].setdefault("log_level", "INFO")

    # Patch sync command timeout (mcp_proxy_adapter uses 30s) for long-running chat.
    command_timeout = 120
    ow = app_config.get("mwps") or {}
    if isinstance(ow, dict):
        command_timeout = int(ow.get("command_execution_timeout_seconds", 120))
    if command_timeout != 30:
        _orig_wait_for = asyncio.wait_for

        def _patched_wait_for(aw, timeout=None, *args, **kwargs):
            if timeout == 30.0:
                timeout = float(command_timeout)
            return _orig_wait_for(aw, timeout=timeout, *args, **kwargs)

        asyncio.wait_for = _patched_wait_for
        print(
            "Command execution timeout patched: 30s -> %ss" % command_timeout,
            file=sys.stderr,
        )

    cfg = get_config()
    cfg.config_path = str(cfg_path)
    setattr(cfg, "model", model)
    cfg.config_data = app_config
    if hasattr(cfg, "feature_manager"):
        cfg.feature_manager.config_data = cfg.config_data

    if server_id == "database-server":
        app_title = "Database Server Adapter"
        app_description = DATABASE_SERVER_DESCRIPTION
    else:
        app_title = "Model Workplace Server Adapter"
        app_description = MWPS_SERVER_DESCRIPTION

    app = create_app(
        title=app_title,
        description=app_description,
        version="1.0.0",
        app_config=app_config,
        config_path=str(cfg_path),
    )

    register_commands()

    host = app_config.get("server", {}).get("host", "0.0.0.0")
    port = int(app_config.get("server", {}).get("port", 8443))

    server_config = {
        "host": host,
        "port": port,
        "log_level": "info",
        "reload": False,
    }
    try:
        ssl_engine_config = build_server_ssl_config(app_config)
        if ssl_engine_config:
            server_config.update(ssl_engine_config)
    except ValueError as e:
        print(f"SSL config error: {e}", file=sys.stderr)
        return 1

    engine = ServerEngineFactory.get_engine("hypercorn")
    if not engine:
        print("Hypercorn engine not available", file=sys.stderr)
        return 1

    engine.run_server(app, server_config)
    return 0


if __name__ == "__main__":
    sys.exit(main())
