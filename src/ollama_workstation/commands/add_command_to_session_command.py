"""
Adapter command: add_command_to_session — add command to session; step 13.

Rejects if command is in config forbidden_commands; logs and returns error.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult

from ..config import load_config
from .session_init_command import _get_session_store

logger = logging.getLogger(__name__)


class AddCommandToSessionCommand(Command):
    """
    Add command_id to session allowed (or remove from forbidden).
    Config forbidden_commands: do not add; log and return error.
    """

    name = "add_command_to_session"
    descr = (
        "Add command_id to session allowed and remove from forbidden. Fails if "
        "command_id is in config forbidden_commands. Needs session_id and command_id."
    )

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Return JSON Schema for parameters: session_id, command_id."""
        return {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session UUID4 from session_init.",
                },
                "command_id": {
                    "type": "string",
                    "description": (
                        "Command name to allow (e.g. echo, ollama_chat, or a command "
                        "from another server in the proxy)."
                    ),
                },
            },
            "required": ["session_id", "command_id"],
        }

    @classmethod
    def get_result_schema(cls) -> Dict[str, Any]:
        """Return JSON Schema for success result with ok boolean."""
        return {"type": "object", "properties": {"ok": {"type": "boolean"}}}

    @classmethod
    def get_error_schema(cls) -> Dict[str, Any]:
        """Return JSON Schema for error result with message."""
        return {
            "type": "object",
            "properties": {"message": {"type": "string"}},
        }

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Return command metadata: name, description, schemas."""
        return {
            "name": cls.name,
            "description": (cls.descr or "").strip(),
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
        # Check config forbidden_commands when config is available
        if config_path:
            try:
                config = load_config(config_path)
                if config.commands_policy_config:
                    cpc = config.commands_policy_config
                    forbidden = cpc.forbidden_commands
                    if command_id in forbidden:
                        logger.error(
                            "add_command_to_session: command %s forbidden " "by config",
                            command_id,
                        )
                        msg = (
                            "command %s is forbidden by config and "
                            "cannot be added to session"
                        ) % command_id
                        return ErrorResult(message=msg, code=-32602)
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "add_command_to_session: could not load config: %s",
                    e,
                )
        try:
            store = _get_session_store(config_path)
            session = store.get(session_id)
            if not session:
                return ErrorResult(message="Session not found", code=-32602)
            new_allowed = list(session.allowed_commands)
            if command_id not in new_allowed:
                new_allowed.append(command_id)
            new_forbidden = [c for c in session.forbidden_commands if c != command_id]
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
