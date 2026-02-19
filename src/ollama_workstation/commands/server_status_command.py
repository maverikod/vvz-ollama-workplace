"""
Adapter command: server_status — report loading state or ready.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from typing import Any, Dict

from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult

from ..model_loading_state import get_state


class ServerStatusCommand(Command):
    """
    Return server status: ready or loading_models; optional current_model/msg.
    Use to see if the adapter is still pulling models at startup.
    """

    name = "server_status"
    descr = (
        "Return status: ready or loading_models; when loading, "
        "current_model and message."
    )

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """No parameters."""
        return {"type": "object", "properties": {}, "required": []}

    @classmethod
    def get_result_schema(cls) -> Dict[str, Any]:
        """Result: status, current_model, message."""
        return {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["ready", "loading_models"],
                    "description": "ready or loading_models",
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
                        "current_model": None,
                        "message": None,
                    },
                },
                "loading": {
                    "success": True,
                    "data": {
                        "status": "loading_models",
                        "current_model": "llama3.2",
                        "message": "Loading model llama3.2...",
                    },
                },
            },
        }

    async def execute(self, **kwargs: Any) -> Any:
        """Return current loading state."""
        return SuccessResult(data=get_state())
