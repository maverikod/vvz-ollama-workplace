"""
OLLAMA workstation adapter commands.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from .ollama_chat_command import OllamaChatCommand
from .server_status_command import ServerStatusCommand

__all__ = ["OllamaChatCommand", "ServerStatusCommand"]
