#!/usr/bin/env python3
"""
Generate adapter_config with same settings as working config, plus all commercial
providers and OLLAMA container. Reads config/adapter_config.json, overlays
ollama_workstation with full model_providers and container, writes to output path.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import json
import os
import sys
from pathlib import Path

# Same structure as working config; add all providers and container.
OLLAMA_WORKSTATION_FULL = {
    "ollama_base_url": "http://127.0.0.1:11434",
    "model_server_url": "http://127.0.0.1:11434",
    "ollama_model": "llama3.2",
    "ollama_models": [
        "llama3.2",
        "gemini-2.0-flash",
        "gpt-4o-mini",
        "claude-3-5-haiku-20241022",
        "grok-2",
        "deepseek-chat",
    ],
    "available_providers": [
        "ollama",
        "google",
        "anthropic",
        "openai",
        "xai",
        "deepseek",
        "openrouter",
    ],
    "model_providers": {
        "ollama": {"url": "http://127.0.0.1:11434"},
        "google": {
            "url": "https://generativelanguage.googleapis.com/v1beta",
            "api_key": "YOUR_GOOGLE_API_KEY",
        },
        "anthropic": {
            "url": "https://api.anthropic.com/v1",
            "api_key": "YOUR_ANTHROPIC_API_KEY",
        },
        "openai": {
            "url": "https://api.openai.com/v1",
            "api_key": "YOUR_OPENAI_API_KEY",
        },
        "xai": {
            "url": "https://api.x.ai/v1",
            "api_key": "YOUR_XAI_GROK_API_KEY",
        },
        "deepseek": {
            "url": "https://api.deepseek.com/v1",
            "api_key": "YOUR_DEEPSEEK_API_KEY",
        },
        "openrouter": {
            "url": "https://openrouter.ai/api/v1",
            "api_key": "YOUR_OPENROUTER_API_KEY",
        },
    },
    "model_server_container_name": "ollama",
    "model_server_image": "ollama/ollama",
    "ollama_timeout": 120,
    "max_tool_rounds": 10,
    "allowed_commands": [],
    "forbidden_commands": [],
    "commands_policy": "allow_by_default",
    "command_discovery_interval_sec": 0,
    "session_store_type": "memory",
    "redis_host": "localhost",
    "redis_port": 6379,
    "redis_key_prefix": "message",
    "max_context_tokens": 4096,
    "last_n_messages": 10,
    "min_semantic_tokens": 256,
    "min_documentation_tokens": 0,
    "relevance_slot_mode": "fixed_order",
    "max_model_call_depth": 1,
    "model_calling_tool_allow_list": [],
    "google_api_key": "YOUR_GOOGLE_API_KEY",
    "anthropic_api_key": "YOUR_ANTHROPIC_API_KEY",
    "openai_api_key": "YOUR_OPENAI_API_KEY",
    "xai_api_key": "YOUR_XAI_GROK_API_KEY",
    "deepseek_api_key": "YOUR_DEEPSEEK_API_KEY",
    "openrouter_api_key": "YOUR_OPENROUTER_API_KEY",
}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    input_path = root / "config" / "adapter_config.json"
    output_path = root / "config" / "adapter_config.generated.json"
    if len(sys.argv) > 1:
        output_path = Path(sys.argv[1])

    if not input_path.exists():
        print("Input config not found: %s" % input_path, file=sys.stderr)
        return 1

    data = json.loads(input_path.read_text(encoding="utf-8"))
    existing_proxy_url = data.get("ollama_workstation", {}).get(
        "mcp_proxy_url"
    ) or data.get("registration", {}).get("register_url", "").replace("/register", "")
    resolved_proxy_url = os.getenv("MCP_PROXY_URL", existing_proxy_url)
    if not resolved_proxy_url:
        print(
            "MCP proxy URL is not set. "
            "Define ollama_workstation.mcp_proxy_url in input config "
            "or export MCP_PROXY_URL.",
            file=sys.stderr,
        )
        return 1

    full_ollama_workstation = dict(OLLAMA_WORKSTATION_FULL)
    full_ollama_workstation["mcp_proxy_url"] = resolved_proxy_url
    data["ollama_workstation"] = full_ollama_workstation

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("Wrote %s" % output_path, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
