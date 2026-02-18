#!/usr/bin/env python3
"""
Minimal example: send one user message to the ollama_chat command and print the reply.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

Requires: server running with ollama_workstation registered (e.g. adapter with
register_ollama_workstation(registry)). Set OLLAMA_WORKSTATION_* env vars or
a config file so the server has proxy and OLLAMA URLs and model.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Add src to path when running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))  # noqa: E402

from mcp_proxy_adapter.client.jsonrpc_client import JsonRpcClient  # noqa: E402


async def main() -> None:
    # Adapter server (where ollama_chat is registered)
    host = os.environ.get("ADAPTER_HOST", "127.0.0.1")
    port = int(os.environ.get("ADAPTER_PORT", "8080"))
    protocol = os.environ.get("ADAPTER_PROTOCOL", "http")

    client = JsonRpcClient(protocol=protocol, host=host, port=port)
    try:
        result = await client.execute_command(
            "ollama_chat",
            {
                "messages": [
                    {"role": "user", "content": "List available servers."},
                ],
            },
        )
        data = result.get("data", {})
        message = data.get("message", "")
        print("Model reply:", message or "(empty)")
        if data.get("history"):
            print("(History length:", len(data["history"]), "messages)")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
