"""
Adapter command: session_create — create a new session and persist.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import json
import uuid
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


def _ensure_list(val: Any) -> List[str]:
    """Ensure value is list of strings."""
    if val is None:
        return []
    if isinstance(val, list):
        return [str(x) for x in val]
    return []


class SessionCreateCommand(Command):
    """
    Create a new session. Id generated if not provided.
    """

    name = "session_create"
    descr = (
        "Create a new session and persist. Optional: model, allowed_commands, "
        "forbidden_commands, standards, session_rules, created_at, id, "
        "minimize_context."
    )

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Strict JSON Schema."""
        return {
            "type": "object",
            "description": "Create session; id optional (generated if omitted).",
            "properties": {
                "model": {"type": "string", "description": "Model name."},
                "allowed_commands": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Allowed command names.",
                },
                "forbidden_commands": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Forbidden command names.",
                },
                "standards": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Standards list.",
                },
                "session_rules": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Session rules.",
                },
                "created_at": {"type": "string", "description": "ISO 8601."},
                "id": {"type": "string", "description": "Session id (optional)."},
                "minimize_context": {
                    "type": "boolean",
                    "description": "Minimize context flag.",
                },
            },
            "required": [],
            "additionalProperties": False,
        }

    async def execute(self, **kwargs: Any) -> Any:
        """Build session, persist to Redis, return session object."""
        app_config = _get_config()
        redis_client = get_redis_client(app_config)
        if redis_client is None:
            return ErrorResult(
                message="Storage backend is not redis or Redis not configured",
                code=-32600,
            )
        _, sess_prefix = get_storage_prefixes(app_config)
        session_id = (kwargs.get("id") or str(uuid.uuid4())).strip()
        model = (kwargs.get("model") or "").strip() or ""
        allowed = _ensure_list(kwargs.get("allowed_commands"))
        forbidden = _ensure_list(kwargs.get("forbidden_commands"))
        standards = _ensure_list(kwargs.get("standards"))
        session_rules = _ensure_list(kwargs.get("session_rules"))
        created_at = (kwargs.get("created_at") or "").strip() or ""
        minimize_context = bool(kwargs.get("minimize_context", False))
        key = "%s:%s" % (sess_prefix, session_id)
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
