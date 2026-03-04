#!/usr/bin/env python3
"""
Check that each configured model can use tools (echo or help).
Sends one chat per model with a prompt to call echo('ping') or help();
reports OK/FAIL. Requires proxy reachable for discovery and tool execution.

Usage:
  ADAPTER_CONFIG_PATH=config/adapter_config.generated.json \\
  python scripts/check_tools_access.py

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Add project root and src so ollama_workstation is importable
_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
_src = _root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from ollama_workstation.chat_flow import run_chat_flow  # noqa: E402
from ollama_workstation.command_alias_registry import CommandAliasRegistry  # noqa: E402
from ollama_workstation.command_discovery import CommandDiscovery  # noqa: E402
from ollama_workstation.config import load_config, WorkstationConfig  # noqa: E402
from ollama_workstation.effective_tool_list_builder import (  # noqa: E402
    EffectiveToolListBuilder,
)
from ollama_workstation.ollama_representation import (  # noqa: E402
    OllamaRepresentation,
    register_ollama_models,
)
from ollama_workstation.proxy_client import ProxyClient  # noqa: E402
from ollama_workstation.representation_registry import (  # noqa: E402
    RepresentationRegistry,
)
from ollama_workstation.safe_name_translator import SafeNameTranslator  # noqa: E402
from ollama_workstation.session_entity import Session  # noqa: E402
from ollama_workstation.tools import MODEL_HELP_TOOL  # noqa: E402
from ollama_workstation.tool_call_registry import ToolCallRegistry  # noqa: E402

TOOL_PROMPT = (
    "Call the echo tool with message 'ping' and reply with the result. "
    "If echo is not available, call the help tool with no parameters "
    "and reply with the first 200 characters."
)
TIMEOUT_ROUNDS = 5


def _config_path() -> Path:
    p = os.environ.get("ADAPTER_CONFIG_PATH")
    if p and Path(p).exists():
        return Path(p)
    for name in (
        "config/adapter_config.generated.json",
        "config/adapter_config.json",
        "config/adapter_config.local.json",
    ):
        path = _root / name
        if path.exists():
            return path
    return _root / "config/adapter_config.json"


async def _build_tools(config: WorkstationConfig) -> tuple[list, ToolCallRegistry]:
    """Build session tools (discovered + help) and registry. Uses minimal session."""
    proxy = ProxyClient(config)
    discovery = CommandDiscovery(
        proxy,
        discovery_interval_sec=getattr(config, "command_discovery_interval_sec", 0)
        or 0,
    )
    await discovery.refresh()
    discovered = discovery.get_discovered_commands(available_only=False)
    builder = EffectiveToolListBuilder(
        CommandAliasRegistry(),
        SafeNameTranslator(),
    )
    default_model = getattr(config, "ollama_model", None) or "llama3.2"
    session = Session.create(model=default_model)
    _tool_list, tool_registry = builder.build(
        session,
        config.commands_policy_config,
        discovered,
        preferred_server_id=getattr(config, "adapter_server_id", None),
    )
    return _tool_list, tool_registry


async def _check_one(
    config: WorkstationConfig,
    model: str,
    tool_list: list,
    tool_registry: ToolCallRegistry,
    registry: RepresentationRegistry,
) -> tuple[bool, str]:
    """Run one chat for model with TOOL_PROMPT; return (ok, detail)."""
    representation = registry.get_representation(model)
    session_tools = representation.serialize_tools(tool_list) + [MODEL_HELP_TOOL]
    messages = [{"role": "user", "content": TOOL_PROMPT}]
    try:
        result = await run_chat_flow(
            config=config,
            messages=messages,
            model=model,
            stream=False,
            max_tool_rounds=TIMEOUT_ROUNDS,
            session_tools=session_tools,
            tool_registry=tool_registry,
        )
    except Exception as e:  # noqa: BLE001
        return False, str(e)[:200]
    err = result.get("error")
    if err:
        return False, err[:200]
    reply = (result.get("message") or "").strip()
    history = result.get("history") or []
    has_tool = any(
        m.get("role") == "assistant" and (m.get("tool_calls") or []) for m in history
    )
    if not reply and not has_tool:
        return False, "empty reply and no tool calls"
    detail = reply[:120] if reply else ("tool_calls in history" if has_tool else "ok")
    return True, detail


async def main_async() -> int:
    config_path = _config_path()
    if not config_path.exists():
        print("Config not found: %s" % config_path, file=sys.stderr)
        return 1
    config = load_config(str(config_path))
    models = list(getattr(config, "ollama_models", None) or ())
    if not models and getattr(config, "ollama_model", None):
        models = [config.ollama_model]
    if not models:
        print("No models in config (ollama_models / ollama_model).", file=sys.stderr)
        return 1
    rep_registry = RepresentationRegistry(default=OllamaRepresentation())
    register_ollama_models(rep_registry, models)
    print("Config: %s" % config_path, file=sys.stderr)
    print("Models: %s" % ", ".join(models), file=sys.stderr)
    print("Prompt: %s" % TOOL_PROMPT[:80] + "...", file=sys.stderr)
    print("-" * 60)
    try:
        tool_list, tool_registry = await _build_tools(config)
    except Exception as e:  # noqa: BLE001
        print("Tool build failed: %s" % e, file=sys.stderr)
        return 1
    failed = 0
    for model in models:
        ok, detail = await _check_one(
            config, model, tool_list, tool_registry, rep_registry
        )
        if ok:
            print("[OK] %s -> %s" % (model, detail))
        else:
            print("[FAIL] %s -> %s" % (model, detail))
            failed += 1
    print("-" * 60)
    print("Passed: %s, Failed: %s" % (len(models) - failed, failed))
    return 1 if failed else 0


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())
