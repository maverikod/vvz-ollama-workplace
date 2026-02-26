"""
Adapter command: set_default_model — hot-swap runtime default OLLAMA model.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from typing import Any, Dict

from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult

from ..model_loading_state import get_active_model, set_active_model


class SetDefaultModelCommand(Command):
    """
    Set runtime default model for new chats (hot-swap without restart).
    Pass model name to set; omit or pass empty to reset to config.ollama_model.
    """

    name = "set_default_model"
    descr = (
        "Set the runtime default OLLAMA model for new chats. No restart needed. "
        "Use empty string or omit to reset to config default. Returns new active_model."
    )

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Parameters: optional model (string)."""
        return {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "Model name as default; empty to reset to config",
                },
            },
            "required": [],
        }

    @classmethod
    def get_result_schema(cls) -> Dict[str, Any]:
        """Result: ok, active_model (null if using config)."""
        return {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean"},
                "active_model": {
                    "type": ["string", "null"],
                    "description": "Current default model; null = use config",
                },
            },
            "required": ["ok", "active_model"],
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
                "set": {
                    "success": True,
                    "data": {"ok": True, "active_model": "qwen2.5-coder:1.5b"},
                },
                "reset": {
                    "success": True,
                    "data": {"ok": True, "active_model": None},
                },
            },
        }

    async def execute(self, **kwargs: Any) -> Any:
        """Set or reset runtime default model."""
        model: str | None = kwargs.get("model")
        set_active_model(model)
        return SuccessResult(data={"ok": True, "active_model": get_active_model()})
