"""
OLLAMA workstation adapter commands.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from .add_command_to_session_command import AddCommandToSessionCommand
from .get_model_context_command import GetModelContextCommand
from .invoke_tool_command import InvokeToolCommand
from .ollama_chat_command import OllamaChatCommand
from .remove_command_from_session_command import (
    RemoveCommandFromSessionCommand,
)
from .server_status_command import ServerStatusCommand
from .session_init_command import SessionInitCommand
from .session_update_command import SessionUpdateCommand
from .set_default_model_command import SetDefaultModelCommand

__all__ = [
    "AddCommandToSessionCommand",
    "GetModelContextCommand",
    "InvokeToolCommand",
    "OllamaChatCommand",
    "RemoveCommandFromSessionCommand",
    "ServerStatusCommand",
    "SessionInitCommand",
    "SessionUpdateCommand",
    "SetDefaultModelCommand",
]
