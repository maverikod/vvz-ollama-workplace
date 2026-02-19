#!/usr/bin/env python3
"""
Run MCP Proxy Adapter with OLLAMA: load config, register command, start server.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import argparse
import json
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

from ollama_workstation.docker_config_validation import validate_project_config


def register_commands() -> None:
    """Register OLLAMA workstation command with adapter registry."""
    from ollama_workstation.registration import register_ollama_workstation

    register_ollama_workstation(registry)


def main() -> int:
    """Load config, validate, create app, register commands, run hypercorn."""
    parser = argparse.ArgumentParser(description="OLLAMA + MCP Adapter (mTLS)")
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

    # 2. Project-specific validation
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

    cfg = get_config()
    cfg.config_path = str(cfg_path)
    setattr(cfg, "model", model)
    cfg.config_data = app_config
    if hasattr(cfg, "feature_manager"):
        cfg.feature_manager.config_data = cfg.config_data

    app = create_app(
        title="OLLAMA Workstation Adapter",
        description="MCP Adapter with ollama_chat",
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
