"""
Adapter command: session_init — create session, return session_id; step 13.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import redis
from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult

from ..config import load_config
from ..session_store import (
    InMemorySessionStore,
    RedisSessionStore,
    SessionStore,
)

_DEFAULT_CONFIG_PATH = os.environ.get(
    "ADAPTER_CONFIG_PATH", "/app/config/adapter_config.json"
)

_default_memory_store: Optional[SessionStore] = None
_default_redis_store: Optional[SessionStore] = None


def _get_session_store(config_path: Optional[str]) -> SessionStore:
    """
    Return SessionStore from config.
    Memory: shared in-memory. Redis: shared Redis-backed store (sessions table:
    key session:{id}, hash with model, allowed_commands, forbidden_commands,
    standards, session_rules, created_at).
    """
    global _default_memory_store, _default_redis_store
    default_exists = Path(_DEFAULT_CONFIG_PATH).exists()
    path = config_path or (_DEFAULT_CONFIG_PATH if default_exists else None)
    config = load_config(path)
    store_type = (config.session_store_type or "").strip().lower()
    if store_type == "memory":
        if _default_memory_store is None:
            _default_memory_store = InMemorySessionStore()
        return _default_memory_store
    if store_type == "redis":
        if _default_redis_store is None:
            redis_client = redis.Redis(
                host=config.redis_host,
                port=config.redis_port,
                password=config.redis_password or None,
                decode_responses=True,
            )
            _default_redis_store = RedisSessionStore(
                redis_client,
                key_prefix="session",
            )
        return _default_redis_store
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
        "Create a new session and return its session_id (UUID4). Optional: model "
        "(default for this session), allowed_commands (allow-list), "
        "forbidden_commands (forbid-list). Use session_id in session_update and "
        "add_command_to_session / remove_command_from_session."
    )

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Parameters: model, allowed_commands, forbidden_commands (opt)."""
        return {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": (
                        "OLLAMA model id for this session (optional at create). "
                        "Used as default when session is used in ollama_chat."
                    ),
                },
                "allowed_commands": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Allow-list of command names for this session. If set, only "
                        "these commands are available (proxy command IDs)."
                    ),
                },
                "forbidden_commands": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Forbid-list of command names. Cannot be used for this session "
                        "even if allowed by config."
                    ),
                },
                "standards": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Canonical standards text blocks for context. Included in "
                        "context order before session_rules and messages (plan §4.3)."
                    ),
                },
                "session_rules": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Session rules text blocks. Included in context after "
                        "standards, before last N messages (plan §4.3)."
                    ),
                },
            },
            "required": [],
        }

    @classmethod
    def get_result_schema(cls) -> Dict[str, Any]:
        """Return JSON Schema for success result with session_id."""
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
        """Return JSON Schema for error result with message."""
        return {
            "type": "object",
            "properties": {"message": {"type": "string"}},
        }

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Return command metadata: name, description, schemas."""
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
        params = dict(parameters or {})
        # Adapter/proxy may pass command params as kwargs instead of parameters.
        for key in (
            "model",
            "allowed_commands",
            "forbidden_commands",
            "standards",
            "session_rules",
            "id",
            "created_at",
        ):
            if key in kwargs and kwargs[key] is not None:
                params[key] = kwargs[key]
        _logger = logging.getLogger(__name__)
        _logger.debug(
            "session_init params_keys=%s",
            list(params.keys()),
        )
        try:
            store = _get_session_store(config_path)
            session = store.create(params)
            logger = _logger
            if session.standards or session.session_rules:
                logger.info(
                    "session_init created session_id=%s standards=%s rules=%s",
                    session.id,
                    len(session.standards),
                    len(session.session_rules),
                )
            return SuccessResult(data={"session_id": session.id})
        except Exception as e:  # noqa: BLE001
            return ErrorResult(message=str(e), code=-32603)
