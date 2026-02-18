"""
Register OLLAMA workstation command with the adapter registry.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from typing import Any

from .commands import OllamaChatCommand


def register_ollama_workstation(registry: Any) -> None:
    """
    Register the ollama_chat command with the given adapter registry.

    Call this from the main app or a custom-commands hook so that
    ollama_chat is available via JSON-RPC.

    Args:
        registry: CommandRegistry instance
        (e.g. from mcp_proxy_adapter.commands.command_registry).
    """
    registry.register(OllamaChatCommand, "custom")
