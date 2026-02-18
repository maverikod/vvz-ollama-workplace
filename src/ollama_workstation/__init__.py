"""
OLLAMA workstation: chat with OLLAMA using MCP Proxy tools.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from .config import WorkstationConfig, load_config
from .tools import get_ollama_tools
from .proxy_client import ProxyClient, ProxyClientError
from .chat_flow import run_chat_flow
from .commands import OllamaChatCommand
from .registration import register_ollama_workstation

__all__ = [
    "WorkstationConfig",
    "load_config",
    "get_ollama_tools",
    "ProxyClient",
    "ProxyClientError",
    "run_chat_flow",
    "OllamaChatCommand",
    "register_ollama_workstation",
]
