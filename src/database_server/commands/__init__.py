"""
Database-server adapter commands: Redis domain API (message, session).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from typing import Any

from database_server.commands.message_write_command import MessageWriteCommand
from database_server.commands.messages_get_by_session_command import (
    MessagesGetBySessionCommand,
)
from database_server.commands.session_create_command import SessionCreateCommand
from database_server.commands.session_get_command import SessionGetCommand
from database_server.commands.session_update_command import SessionUpdateCommand

COMMAND_CLASSES = (
    MessageWriteCommand,
    MessagesGetBySessionCommand,
    SessionGetCommand,
    SessionCreateCommand,
    SessionUpdateCommand,
)


def register_database_commands(registry: Any) -> None:
    """Register all database-server commands with the adapter registry."""
    for cmd_cls in COMMAND_CLASSES:
        registry.register(cmd_cls, "custom")
