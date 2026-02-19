"""
Register OLLAMA workstation command with the adapter registry.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from typing import Any

from .commands import OllamaChatCommand, ServerStatusCommand


def register_ollama_workstation(registry: Any) -> None:
    """
    Register OLLAMA workstation commands with the given adapter registry.

    Call this from the main app or a custom-commands hook so that
    ollama_chat and server_status are available via JSON-RPC.

    Args:
        registry: CommandRegistry instance
        (e.g. from mcp_proxy_adapter.commands.command_registry).
    """
    registry.register(OllamaChatCommand, "custom")
    registry.register(ServerStatusCommand, "custom")
