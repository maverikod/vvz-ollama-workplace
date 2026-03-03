"""
OLLAMA workstation: chat with OLLAMA using MCP Proxy tools.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import logging
import os
from typing import Optional

from .config import WorkstationConfig, load_config
from .provider_client_base import BaseProviderClient
from .provider_models import CHEAPEST_MODEL_BY_PROVIDER, get_cheapest_model
from .tools import get_ollama_tools
from .proxy_client import ProxyClient, ProxyClientError
from .chat_flow import run_chat_flow
from .commands import OllamaChatCommand
from .registration import register_ollama_workstation

_OW_LOGGER_NAME = "ollama_workstation"
_ow_file_handler: Optional[logging.FileHandler] = None


def _setup_file_logging() -> None:
    """Add a file handler for ollama_workstation so logs go to a separate file."""
    global _ow_file_handler
    if _ow_file_handler is not None:
        return
    # Default to /tmp when not in container so we don't require /app.
    log_dir = os.environ.get("ADAPTER_LOG_DIR", "/tmp")
    log_file = os.environ.get(
        "OLLAMA_WORKSTATION_LOG_FILE",
        os.path.join(log_dir, "ollama_workstation.log"),
    )
    for path_candidate in (log_file, "/tmp/ollama_workstation.log"):
        try:
            d = os.path.dirname(path_candidate)
            if d:
                os.makedirs(d, exist_ok=True)
            _ow_file_handler = logging.FileHandler(path_candidate, encoding="utf-8")
            _ow_file_handler.setLevel(logging.DEBUG)
            _ow_file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
            logger = logging.getLogger(_OW_LOGGER_NAME)
            logger.setLevel(logging.INFO)
            logger.addHandler(_ow_file_handler)
            break
        except OSError as e:
            logging.getLogger(__name__).warning(
                "ollama_workstation file logging failed for %s: %s",
                path_candidate,
                e,
            )
            continue


_setup_file_logging()

__all__ = [
    "BaseProviderClient",
    "CHEAPEST_MODEL_BY_PROVIDER",
    "WorkstationConfig",
    "get_cheapest_model",
    "load_config",
    "get_ollama_tools",
    "ProxyClient",
    "ProxyClientError",
    "run_chat_flow",
    "OllamaChatCommand",
    "register_ollama_workstation",
]
