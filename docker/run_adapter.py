#!/usr/bin/env python3
"""
Run MCP Proxy Adapter with OLLAMA: load config, register command, start server.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import argparse
import asyncio
import json
import logging
import sys
import threading
import time
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
from ollama_workstation.model_loading_state import (
    set_loading,
    set_model_ready,
    set_ready,
)
from ollama_workstation.model_loader import run_model_loading, warm_up_models
from ollama_workstation.ollama_client import start_readiness_ping_thread

# So that chat_flow, ollama_chat_command, proxy_client INFO appear in adapter logs.
logging.getLogger("ollama_workstation").setLevel(logging.INFO)

# Server description for proxy catalog.
OLLAMA_WORKSTATION_SERVER_DESCRIPTION = (
    "OLLAMA Workstation: MCP adapter that runs chat with local OLLAMA and gives the "
    "model access to MCP Proxy tools (list_servers, call_server, help). Use "
    "ollama_chat to send messages and get replies; model can call any server. "
    "Session commands (session_init, session_update, add_command_to_session, "
    "remove_command_from_session) manage per-session allow/forbid lists. "
    "server_status reports adapter readiness or model loading."
)

DATABASE_SERVER_DESCRIPTION = (
    "Database Server: MCP adapter exposing Redis domain API. Commands: "
    "message_write, messages_get_by_session, session_get, session_create, "
    "session_update. Full command catalog with strict JSON Schema; mTLS."
)


def register_commands() -> None:
    """Register commands by server_id: ollama-server | workstation | database-server."""
    cfg = get_config()
    cfg_data = getattr(cfg, "config_data", None) or {}
    server_id = str((cfg_data.get("registration") or {}).get("server_id") or "").strip()
    if server_id == "database-server":
        from database_server.commands import register_database_commands

        register_database_commands(registry)
    elif server_id == "ollama-server":
        from ollama_workstation.registration import register_ollama_server

        register_ollama_server(registry)
    else:
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
    ow = app_config.get("ollama_workstation") or {}
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
        app_title = "OLLAMA Workstation Adapter"
        app_description = OLLAMA_WORKSTATION_SERVER_DESCRIPTION

    app = create_app(
        title=app_title,
        description=app_description,
        version="1.0.0",
        app_config=app_config,
        config_path=str(cfg_path),
    )

    register_commands()

    ow = app_config.get("ollama_workstation") or {}
    oo = (ow.get("ollama") or {}) if isinstance(ow, dict) else {}
    model_list: list[str] = []
    model_server_url = ""
    if server_id != "database-server" and isinstance(ow, dict):
        model_server_url = (
            oo.get("model_server_url") or oo.get("base_url") or "http://127.0.0.1:11434"
        ).strip()
        start_readiness_ping_thread(model_server_url)
        model_list = list(oo.get("models") or [])
        if not model_list and oo.get("model"):
            model_list = [str(oo.get("model", "")).strip()]
        model_list = [m for m in model_list if isinstance(m, str) and m.strip()]

    def _model_loading_worker() -> None:
        """Run in background: ensure container if configured, load and warm via API."""
        set_loading(None, "Model loading started...")
        print("Model loading started (background). Use server_status.", file=sys.stderr)
        t0 = time.perf_counter()
        try:
            run_model_loading(str(cfg_path))
            if model_list and model_server_url:
                timeout = float(oo.get("timeout", 120))
                warm_up_models(model_server_url, model_list, timeout_sec=timeout)
            set_model_ready(True)
            set_ready()
            print(
                "Model loading finished in %.2fs" % (time.perf_counter() - t0),
                file=sys.stderr,
            )
        except Exception as e:
            print("Model loading failed: %s" % e, file=sys.stderr)
            set_ready()
            set_model_ready(False)

    if model_list or ow:
        t = threading.Thread(
            target=_model_loading_worker, daemon=True, name="model-load"
        )
        t.start()
        print(
            "Server starting; model loading in background. Use server_status.",
            file=sys.stderr,
        )
    else:
        set_model_ready(True)

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
