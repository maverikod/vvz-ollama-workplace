"""
Adapter command: session_init — create session, return session_id; step 13.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult

from ..config import load_config
from ..session_store import SessionStore, InMemorySessionStore

_DEFAULT_CONFIG_PATH = os.environ.get(
    "ADAPTER_CONFIG_PATH", "/app/config/adapter_config.json"
)


_default_memory_store: Optional[SessionStore] = None


def _get_session_store(config_path: Optional[str]) -> SessionStore:
    """
    Return SessionStore from config.
    Shared in-memory store when type is memory.
    """
    global _default_memory_store
    default_exists = Path(_DEFAULT_CONFIG_PATH).exists()
    path = config_path or (_DEFAULT_CONFIG_PATH if default_exists else None)
    config = load_config(path)
    if (config.session_store_type or "").strip().lower() == "memory":
        if _default_memory_store is None:
            _default_memory_store = InMemorySessionStore()
        return _default_memory_store
    if _default_memory_store is None:
        _default_memory_store = InMemorySessionStore()
    return _default_memory_store


class SessionInitCommand(Command):
    """
    Create a new session. Request: command name, parameters (model, lists).
    Response: { session_id: "<uuid4>" }.
    """

    name = "session_init"
    descr = (
        "Create session. Params: model, allowed_commands, "
        "forbidden_commands. Returns session_id (UUID4)."
    )

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Parameters: model, allowed_commands, forbidden_commands (opt)."""
        return {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "Model id (optional at create).",
                },
                "allowed_commands": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional allow-list for this session.",
                },
                "forbidden_commands": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional forbid-list for this session.",
                },
            },
            "required": [],
        }

    @classmethod
    def get_result_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "New session UUID4.",
                },
            },
            "required": ["session_id"],
        }

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
        """Create session via SessionStore.create(parameters); return id."""
        params = parameters or {}
        try:
            store = _get_session_store(config_path)
            session = store.create(params)
            return SuccessResult(data={"session_id": session.id})
        except Exception as e:  # noqa: BLE001
            return ErrorResult(message=str(e), code=-32603)
