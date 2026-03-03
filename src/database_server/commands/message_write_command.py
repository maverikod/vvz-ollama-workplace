"""
Adapter command: message_write — write one message record to Redis.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from typing import Any, Dict

from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult

from database_server.redis_facade import get_redis_client, get_storage_prefixes


def _get_config() -> dict:
    """Return app config from adapter config singleton."""
    try:
        from mcp_proxy_adapter.config import get_config

        cfg = get_config()
        return getattr(cfg, "config_data", None) or {}
    except Exception:
        return {}


class MessageWriteCommand(Command):
    """
    Write one message record. Key: {message_key_prefix}:{uuid}; value: hash.
    """

    name = "message_write"
    descr = (
        "Write one message record to storage. Key layout: {prefix}:{uuid}; "
        "fields: uuid, created_at, source, body, session_id."
    )

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Strict JSON Schema; additionalProperties false."""
        return {
            "type": "object",
            "description": (
                "Write one message record (uuid, created_at, source, body, session_id)."
            ),
            "properties": {
                "uuid": {
                    "type": "string",
                    "description": "Message UUID (primary key).",
                },
                "created_at": {"type": "string", "description": "ISO 8601 timestamp."},
                "source": {
                    "type": "string",
                    "enum": ["user", "model", "tool", "external_agent"],
                    "description": "Message source.",
                },
                "body": {"type": "string", "description": "Message content."},
                "session_id": {"type": "string", "description": "Session UUID."},
            },
            "required": ["uuid", "created_at", "source", "body", "session_id"],
            "additionalProperties": False,
        }

    async def execute(self, **kwargs: Any) -> Any:
        """Persist message to Redis; return written key or error."""
        app_config = _get_config()
        redis_client = get_redis_client(app_config)
        if redis_client is None:
            return ErrorResult(
                message="Storage backend is not redis or Redis not configured",
                code=-32600,
            )
        msg_prefix, _ = get_storage_prefixes(app_config)
        uuid_val = kwargs.get("uuid")
        created_at = kwargs.get("created_at")
        source = kwargs.get("source")
        body = kwargs.get("body")
        session_id = kwargs.get("session_id")
        if not uuid_val:
            return ErrorResult(message="uuid is required", code=-32602)
        key = "%s:%s" % (msg_prefix, uuid_val)
        mapping = {
            "uuid": str(uuid_val),
            "created_at": str(created_at or ""),
            "source": str(source or ""),
            "body": str(body or ""),
            "session_id": str(session_id or ""),
        }
        try:
            redis_client.hset(key, mapping=mapping)
        except Exception as e:
            return ErrorResult(message="Redis write failed: %s" % e, code=-32603)
        return SuccessResult(data={"written": True, "key": key})
