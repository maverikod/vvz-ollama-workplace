"""
Register OLLAMA workstation command with the adapter registry.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from typing import Any

from .commands import (
    AddCommandToSessionCommand,
    GetModelContextCommand,
    InvokeToolCommand,
    OllamaChatCommand,
    RemoveCommandFromSessionCommand,
    ServerStatusCommand,
    SessionInitCommand,
    SessionUpdateCommand,
    SetDefaultModelCommand,
)


def register_ollama_workstation(registry: Any) -> None:
    """
    Register OLLAMA workstation commands with the given adapter registry.

    Call this from the main app or a custom-commands hook so that
    ollama_chat, server_status, and session commands are available.

    Args:
        registry: CommandRegistry instance
        (e.g. from mcp_proxy_adapter.commands.command_registry).
    """
    registry.register(OllamaChatCommand, "custom")
    registry.register(ServerStatusCommand, "custom")
    registry.register(SessionInitCommand, "custom")
    registry.register(SessionUpdateCommand, "custom")
    registry.register(AddCommandToSessionCommand, "custom")
    registry.register(RemoveCommandFromSessionCommand, "custom")
    registry.register(GetModelContextCommand, "custom")
    registry.register(InvokeToolCommand, "custom")
    registry.register(SetDefaultModelCommand, "custom")
