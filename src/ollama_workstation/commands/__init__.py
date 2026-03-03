"""
OLLAMA workstation adapter commands.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from .add_command_to_session_command import AddCommandToSessionCommand
from .direct_chat_command import DirectChatCommand
from .get_model_context_command import GetModelContextCommand
from .get_model_state_command import GetModelStateCommand
from .invoke_tool_command import InvokeToolCommand
from .ollama_chat_command import OllamaChatCommand
from .remove_command_from_session_command import (
    RemoveCommandFromSessionCommand,
)
from .server_status_command import ServerStatusCommand
from .session_init_command import SessionInitCommand
from .session_update_command import SessionUpdateCommand
from .set_default_model_command import SetDefaultModelCommand
from .ollama_server_chat_command import OllamaServerChatCommand
from .ollama_server_embed_command import OllamaServerEmbedCommand
from .ollama_server_list_command import OllamaServerListCommand
from .ollama_server_pull_command import OllamaServerPullCommand

__all__ = [
    "AddCommandToSessionCommand",
    "DirectChatCommand",
    "GetModelContextCommand",
    "GetModelStateCommand",
    "InvokeToolCommand",
    "OllamaChatCommand",
    "RemoveCommandFromSessionCommand",
    "ServerStatusCommand",
    "SessionInitCommand",
    "SessionUpdateCommand",
    "SetDefaultModelCommand",
    "OllamaServerChatCommand",
    "OllamaServerEmbedCommand",
    "OllamaServerListCommand",
    "OllamaServerPullCommand",
]
