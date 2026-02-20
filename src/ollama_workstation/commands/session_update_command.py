"""
Adapter command: session_update — set model, allowed/forbidden lists; step 13.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult

from .session_init_command import _get_session_store

_DEFAULT_CONFIG_PATH = os.environ.get(
    "ADAPTER_CONFIG_PATH", "/app/config/adapter_config.json"
)


class SessionUpdateCommand(Command):
    """
    Update session: session_id, optional model, allowed/forbidden_commands.
    """

    name = "session_update"
    descr = "Update session: session_id required; optional model, lists."

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session UUID4.",
                },
                "model": {"type": "string"},
                "allowed_commands": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "forbidden_commands": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["session_id"],
        }

    @classmethod
    def get_result_schema(cls) -> Dict[str, Any]:
        return {"type": "object", "properties": {"ok": {"type": "boolean"}}}

    @classmethod
    def get_error_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {"message": {"type": "string"}},
        }

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        desc = (cls.descr or "").strip()
        return {
            "name": cls.name,
            "description": desc,
            "params_schema": cls.get_schema(),
            "result_schema": cls.get_result_schema(),
            "error_schema": cls.get_error_schema(),
        }

    async def execute(
        self,
        parameters: Optional[Dict[str, Any]] = None,
        config_path: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        params = parameters or {}
        session_id = (params.get("session_id") or "").strip()
        if not session_id:
            return ErrorResult(message="session_id is required", code=-32602)
        try:
            store = _get_session_store(config_path)
            attrs = {}
            if "model" in params:
                attrs["model"] = params.get("model")
            if "allowed_commands" in params:
                attrs["allowed_commands"] = params.get("allowed_commands")
            if "forbidden_commands" in params:
                attrs["forbidden_commands"] = params.get("forbidden_commands")
            store.update(session_id, attrs)
            return SuccessResult(data={"ok": True})
        except KeyError as e:
            return ErrorResult(
                message="Session not found: %s" % e, code=-32602
            )
        except Exception as e:  # noqa: BLE001
            return ErrorResult(message=str(e), code=-32603)
