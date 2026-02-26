"""
Adapter command: get_model_state — read model status and current default model.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from typing import Any, Dict

from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult

from ..model_loading_state import get_state


class GetModelStateCommand(Command):
    """
    Read model state: status (ready or loading_models) and which model is default.
    Returns status, active_model (default for new chats), optional message.
    """

    name = "get_model_state"
    descr = (
        "Read model state: status (ready or loading_models) and default model. "
        "Returns status, active_model (null = use config), current_model and message."
    )

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """No parameters."""
        return {"type": "object", "properties": {}, "required": []}

    @classmethod
    def get_result_schema(cls) -> Dict[str, Any]:
        """Result: status, active_model, current_model, message."""
        return {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["ready", "loading_models"],
                    "description": "ready or loading_models",
                },
                "active_model": {
                    "type": ["string", "null"],
                    "description": "Default model for new chats; null = config",
                },
                "current_model": {
                    "type": ["string", "null"],
                    "description": "Model being loaded, if any",
                },
                "message": {
                    "type": ["string", "null"],
                    "description": "Status message",
                },
            },
            "required": ["status"],
        }

    @classmethod
    def get_error_schema(cls) -> Dict[str, Any]:
        """No specific errors."""
        return {"type": "object", "properties": {}}

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Metadata for the command."""
        return {
            "name": cls.name,
            "description": (cls.__doc__ or cls.descr or "").strip(),
            "params": cls.get_schema(),
            "result_schema": cls.get_result_schema(),
            "error_schema": cls.get_error_schema(),
            "error_codes": [],
            "examples": {
                "ready": {
                    "success": True,
                    "data": {
                        "status": "ready",
                        "active_model": "llama3.2",
                        "current_model": None,
                        "message": None,
                    },
                },
                "loading": {
                    "success": True,
                    "data": {
                        "status": "loading_models",
                        "active_model": None,
                        "current_model": "llama3.2",
                        "message": "Loading model llama3.2...",
                    },
                },
            },
        }

    async def execute(self, **kwargs: Any) -> Any:
        """Return current model state (status and model)."""
        return SuccessResult(data=get_state())
