"""
Adapter command: session_update — update existing session.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult

from database_server.redis_facade import get_redis_client, get_storage_prefixes

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


def _decode_val(val: Any) -> Any:
    """Decode Redis response."""
    if val is None:
        return None
    if isinstance(val, bytes):
        return val.decode("utf-8")
    return str(val) if val else None


def _parse_list(val: Any) -> List[str]:
    """Parse JSON array of strings."""
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


class SessionUpdateCommand(Command):
    """
    Update existing session by id. Error if not found.
    """

    name = "session_update"
    descr = (
        "Update session by session_id. Partial update: only provided fields change. "
        "Returns error if session not found."
    )

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Strict JSON Schema."""
        return {
            "type": "object",
            "description": "Update session by session_id; optional key_prefix.",
            "properties": {
                "session_id": {"type": "string", "description": "Session UUID."},
                "model": {"type": "string", "description": "New model."},
                "allowed_commands": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "New allowed list.",
                },
                "forbidden_commands": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "New forbidden list.",
                },
                "standards": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "New standards.",
                },
                "session_rules": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "New session_rules.",
                },
                "minimize_context": {
                    "type": "boolean",
                    "description": "New minimize_context.",
                },
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
        """Load existing session, merge updates, persist."""
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
            return ErrorResult(
                message="Session not found: %s" % session_id,
                code=-32602,
            )
        model = _decode_val(raw.get(_F_MODEL)) or ""
        allowed = _parse_list(raw.get(_F_ALLOWED))
        forbidden = _parse_list(raw.get(_F_FORBIDDEN))
        standards = _parse_list(raw.get(_F_STANDARDS))
        session_rules = _parse_list(raw.get(_F_SESSION_RULES))
        created_at = _decode_val(raw.get(_F_CREATED_AT)) or ""
        minimize_context = _parse_bool(raw.get(_F_MINIMIZE))
        if "model" in kwargs:
            model = str(kwargs.get("model") or "").strip() or ""
        if "allowed_commands" in kwargs:
            allowed = [str(x) for x in (kwargs.get("allowed_commands") or [])]
        if "forbidden_commands" in kwargs:
            forbidden = [str(x) for x in (kwargs.get("forbidden_commands") or [])]
        if "standards" in kwargs:
            standards = [str(x) for x in (kwargs.get("standards") or [])]
        if "session_rules" in kwargs:
            session_rules = [str(x) for x in (kwargs.get("session_rules") or [])]
        if "minimize_context" in kwargs:
            minimize_context = bool(kwargs.get("minimize_context", False))
        mapping = {
            _F_MODEL: model,
            _F_ALLOWED: json.dumps(allowed),
            _F_FORBIDDEN: json.dumps(forbidden),
            _F_STANDARDS: json.dumps(standards),
            _F_SESSION_RULES: json.dumps(session_rules),
            _F_CREATED_AT: created_at,
            _F_MINIMIZE: "true" if minimize_context else "false",
        }
        try:
            redis_client.hset(key, mapping=mapping)
        except Exception as e:
            return ErrorResult(message="Redis write failed: %s" % e, code=-32603)
        session = {
            "id": session_id,
            "model": model or None,
            "allowed_commands": allowed,
            "forbidden_commands": forbidden,
            "standards": standards,
            "session_rules": session_rules,
            "created_at": created_at or None,
            "minimize_context": minimize_context,
        }
        return SuccessResult(data={"session": session})
