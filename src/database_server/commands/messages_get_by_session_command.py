"""
Adapter command: messages_get_by_session — list messages for a session.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from typing import Any, Dict, List

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


class MessagesGetBySessionCommand(Command):
    """
    Return all messages for session_id, ordered by created_at.
    """

    name = "messages_get_by_session"
    descr = (
        "Return messages for a session. Uses key prefix scan and filters by "
        "session_id; ordered by created_at."
    )

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Strict JSON Schema."""
        return {
            "type": "object",
            "description": "Get messages for session_id; optional key_prefix.",
            "properties": {
                "session_id": {"type": "string", "description": "Session UUID."},
                "key_prefix": {
                    "type": "string",
                    "description": "Key prefix (default: message).",
                    "default": "message",
                },
            },
            "required": ["session_id"],
            "additionalProperties": False,
        }

    async def execute(self, **kwargs: Any) -> Any:
        """Scan keys by prefix, filter by session_id, sort by created_at."""
        app_config = _get_config()
        redis_client = get_redis_client(app_config)
        if redis_client is None:
            return ErrorResult(
                message="Storage backend is not redis or Redis not configured",
                code=-32600,
            )
        msg_prefix, _ = get_storage_prefixes(app_config)
        key_prefix = (kwargs.get("key_prefix") or msg_prefix).strip().rstrip(":")
        session_id = (kwargs.get("session_id") or "").strip()
        if not session_id:
            return ErrorResult(message="session_id is required", code=-32602)
        pattern = "%s:*" % key_prefix
        out: List[Dict[str, Any]] = []
        try:
            for key in redis_client.scan_iter(match=pattern):
                data = redis_client.hgetall(key)
                if not data:
                    continue
                msg = dict(data)
                if msg.get("session_id") == session_id:
                    out.append(msg)
        except Exception as e:
            return ErrorResult(message="Redis scan failed: %s" % e, code=-32603)
        out.sort(key=lambda m: m.get("created_at") or "")
        return SuccessResult(data={"messages": out})
