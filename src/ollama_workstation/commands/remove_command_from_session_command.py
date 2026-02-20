"""
Adapter command: remove_command_from_session; step 13.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult

from .session_init_command import _get_session_store


class RemoveCommandFromSessionCommand(Command):
    """Remove command_id from session allowed list or add to forbidden."""

    name = "remove_command_from_session"
    descr = "Remove a command from the session (allowed or add to forbidden)."

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "command_id": {"type": "string"},
            },
            "required": ["session_id", "command_id"],
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
        command_id = (params.get("command_id") or "").strip()
        if not session_id or not command_id:
            return ErrorResult(
                message="session_id and command_id are required",
                code=-32602,
            )
        try:
            store = _get_session_store(config_path)
            session = store.get(session_id)
            if not session:
                return ErrorResult(message="Session not found", code=-32602)
            new_allowed = [
                c for c in session.allowed_commands if c != command_id
            ]
            new_forbidden = list(session.forbidden_commands) + [command_id]
            store.update(
                session_id,
                {
                    "allowed_commands": new_allowed,
                    "forbidden_commands": new_forbidden,
                },
            )
            return SuccessResult(data={"ok": True})
        except Exception as e:  # noqa: BLE001
            return ErrorResult(message=str(e), code=-32603)
