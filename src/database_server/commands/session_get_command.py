"""
Adapter command: session_get — return session by id.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult

from database_server.redis_facade import get_redis_client, get_storage_prefixes

# Session hash field names (aligned with session_store)
_F_MODEL = "model"
_F_ALLOWED = "allowed_commands"
_F_FORBIDDEN = "forbidden_commands"
_F_STANDARDS = "standards"
_F_SESSION_RULES = "session_rules"
_F_CREATED_AT = "created_at"
_F_MINIMIZE = "minimize_context"


def _get_config() -> dict:
    """Return app config from adapter config singleton."""
    try:
        from mcp_proxy_adapter.config import get_config

        cfg = get_config()
        return getattr(cfg, "config_data", None) or {}
    except Exception:
        return {}


def _decode_val(val: Any) -> Optional[str]:
    """Decode Redis response to string."""
    if val is None:
        return None
    if isinstance(val, bytes):
        return val.decode("utf-8")
    return str(val) if val else None


def _parse_list(val: Any) -> list:
    """Parse JSON array of strings from Redis field."""
    s = _decode_val(val)
    if not s or not str(s).strip():
        return []
    try:
        out = json.loads(s)
        return [str(x) for x in out] if isinstance(out, list) else []
    except (TypeError, ValueError):
        return []


def _parse_bool(val: Any, default: bool = False) -> bool:
    """Parse bool from Redis value."""
    s = _decode_val(val)
    if s is None or not str(s).strip():
        return default
    return str(s).strip().lower() in ("1", "true", "yes")


class SessionGetCommand(Command):
    """
    Return session by id or null if not found.
    """

    name = "session_get"
    descr = "Return session by session_id. Result session object or null."

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Strict JSON Schema."""
        return {
            "type": "object",
            "description": "Get session by session_id; optional key_prefix.",
            "properties": {
                "session_id": {"type": "string", "description": "Session UUID."},
                "key_prefix": {
                    "type": "string",
                    "description": "Key prefix (default: session).",
                    "default": "session",
                },
            },
            "required": ["session_id"],
            "additionalProperties": False,
        }

    async def execute(self, **kwargs: Any) -> Any:
        """Read session hash from Redis; decode to session object."""
        app_config = _get_config()
        redis_client = get_redis_client(app_config)
        if redis_client is None:
            return ErrorResult(
                message="Storage backend is not redis or Redis not configured",
                code=-32600,
            )
        _, sess_prefix = get_storage_prefixes(app_config)
        key_prefix = (kwargs.get("key_prefix") or sess_prefix).strip().rstrip(":")
        session_id = (kwargs.get("session_id") or "").strip()
        if not session_id:
            return ErrorResult(message="session_id is required", code=-32602)
        key = "%s:%s" % (key_prefix, session_id)
        try:
            raw = redis_client.hgetall(key)
        except Exception as e:
            return ErrorResult(message="Redis get failed: %s" % e, code=-32603)
        if not raw:
            return SuccessResult(data={"session": None})
        session = {
            "id": session_id,
            "model": _decode_val(raw.get(_F_MODEL)),
            "allowed_commands": _parse_list(raw.get(_F_ALLOWED)),
            "forbidden_commands": _parse_list(raw.get(_F_FORBIDDEN)),
            "standards": _parse_list(raw.get(_F_STANDARDS)),
            "session_rules": _parse_list(raw.get(_F_SESSION_RULES)),
            "created_at": _decode_val(raw.get(_F_CREATED_AT)),
            "minimize_context": _parse_bool(raw.get(_F_MINIMIZE)),
        }
        return SuccessResult(data={"session": session})
