"""
Adapter command: invoke_tool — run one proxy tool the same way the model does.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult

from ..chat_flow import run_tool_like_model
from ..config import load_config

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_PATH = os.environ.get(
    "ADAPTER_CONFIG_PATH", "/app/config/adapter_config.json"
)


class InvokeToolCommand(Command):
    """
    Invoke a tool the same way the model does; result in model format.

    Uses the same path as the model: tool_name is the display name (e.g. embed,
    echo) from discovery; code resolves to server and calls it directly, then
    returns the result in the format the model would see. Also supports
    list_servers, call_server, help for debugging.
    """

    name = "invoke_tool"
    descr = (
        "Invoke a tool like the model: tool_name is the display name (e.g. embed, "
        "echo). Same resolution and direct server call as in chat; result is "
        "converted to the format the model sees. Params: tool_name, arguments."
    )

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Parameters: tool_name (display name as model sees), arguments (dict)."""
        return {
            "type": "object",
            "properties": {
                "tool_name": {
                    "type": "string",
                    "description": (
                        "Tool display name as the model sees it (e.g. embed, echo), "
                        "or list_servers, call_server, help for debugging."
                    ),
                    "example": "embed",
                },
                "arguments": {
                    "type": "object",
                    "description": (
                        'Arguments for the tool (e.g. {"text": "..."} for embed). '
                        "For list_servers: optional page, page_size, filter_enabled."
                    ),
                    "example": {"text": "hello"},
                },
            },
            "required": ["tool_name"],
            "additionalProperties": False,
        }

    @classmethod
    def get_result_schema(cls) -> Dict[str, Any]:
        """Success result: content (tool output string)."""
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": (
                        "Tool result in the format the model sees (same as tool "
                        "message content after resolution and direct server call)."
                    ),
                },
            },
            "required": ["content"],
        }

    @classmethod
    def get_error_schema(cls) -> Dict[str, Any]:
        """Error result: message (string)."""
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Human-readable error message",
                },
            },
        }

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Complete metadata: name, description, schemas, error_codes, examples."""
        return {
            "name": cls.name,
            "description": (cls.__doc__ or cls.descr or "").strip(),
            "params_schema": cls.get_schema(),
            "result_schema": cls.get_result_schema(),
            "error_schema": cls.get_error_schema(),
            "error_codes": [
                {
                    "code": -32602,
                    "description": "Invalid parameters",
                    "when": "tool_name missing or empty",
                },
                {
                    "code": -32603,
                    "description": "Internal error",
                    "when": (
                        "Config load failed or proxy call failed "
                        "(e.g. connection refused, timeout)."
                    ),
                },
            ],
            "examples": {
                "embed": {
                    "success": True,
                    "data": {
                        "content": '{"embedding": [0.1, ...], "model": "..."}',
                    },
                },
                "list_servers": {
                    "success": True,
                    "data": {
                        "content": '{"servers": [...], "pagination": {...}}',
                    },
                },
                "error": {
                    "success": False,
                    "error": {
                        "code": -32603,
                        "message": "Connection refused to proxy",
                    },
                },
            },
        }

    async def execute(
        self,
        parameters: Optional[Dict[str, Any]] = None,
        config_path: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        params = dict(parameters or {})
        for key in ("tool_name", "arguments"):
            if key in kwargs and kwargs[key] is not None:
                params[key] = kwargs[key]
        tool_name = (params.get("tool_name") or "").strip()
        if not tool_name:
            return ErrorResult(message="tool_name is required", code=-32602)
        arguments = params.get("arguments")
        if not isinstance(arguments, dict):
            arguments = {}
        default_exists = Path(_DEFAULT_CONFIG_PATH).exists()
        path = config_path or (_DEFAULT_CONFIG_PATH if default_exists else None)
        try:
            config = load_config(path)
        except Exception as e:  # noqa: BLE001
            logger.warning("invoke_tool config load failed: %s", e)
            return ErrorResult(message=str(e), code=-32603)
        try:
            content = await run_tool_like_model(config, tool_name, arguments)
            return SuccessResult(data={"content": content})
        except Exception as e:  # noqa: BLE001
            logger.exception("invoke_tool failed: %s", e)
            return ErrorResult(message=str(e), code=-32603)
