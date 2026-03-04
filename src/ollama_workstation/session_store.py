"""
SessionStore interface and implementations: in-memory, Redis; step 05.

Sessions table (Redis): key {prefix}:{session_id}, hash with model,
allowed_commands, forbidden_commands, standards, session_rules, created_at,
minimize_context (arrays stored as JSON; minimize_context as "true"/"false").
Standards and session_rules are persisted per plan §3.5.2.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .session_entity import Session

# Redis hash field names for session attributes
_SESSION_FIELD_MODEL = "model"
_SESSION_FIELD_ALLOWED = "allowed_commands"
_SESSION_FIELD_FORBIDDEN = "forbidden_commands"
_SESSION_FIELD_STANDARDS = "standards"
_SESSION_FIELD_SESSION_RULES = "session_rules"
_SESSION_FIELD_CREATED_AT = "created_at"
_SESSION_FIELD_MINIMIZE_CONTEXT = "minimize_context"


def _decode_val(val: Any) -> Optional[str]:
    """Return string from Redis response (bytes or str)."""
    if val is None:
        return None
    if isinstance(val, bytes):
        return val.decode("utf-8")
    return str(val) if val else None


def _parse_list_json(val: Any) -> List[str]:
    """Parse JSON array of strings from Redis field; return list of str."""
    s = _decode_val(val)
    if not s or not s.strip():
        return []
    try:
        out = json.loads(s)
        if isinstance(out, list):
            return [str(x) for x in out]
        return []
    except (TypeError, ValueError):
        return []


def _parse_bool(val: Any, default: bool = False) -> bool:
    """Parse bool from Redis response (e.g. 'true', '1')."""
    s = _decode_val(val)
    if s is None or not s.strip():
        return default
    return s.strip().lower() in ("1", "true", "yes")


class SessionStore(ABC):
    """
    Persistence for Session: get, create, update.
    Attrs include model, allowed_commands, forbidden_commands, standards,
    session_rules (plan §3.5.2). Config forbidden_commands not stored here.
    """

    @abstractmethod
    def get(self, session_id: str) -> Optional[Session]:
        """Return session by id or None if not found."""
        raise NotImplementedError

    @abstractmethod
    def create(self, attrs: Dict[str, Any]) -> Session:
        """Create session; attrs include model, lists, standards, session_rules."""
        raise NotImplementedError

    @abstractmethod
    def update(self, session_id: str, attrs: Dict[str, Any]) -> Session:
        """Update session; attrs partial. Raises if not found."""
        raise NotImplementedError


class InMemorySessionStore(SessionStore):
    """In-memory SessionStore for tests and single-process use."""

    def __init__(self) -> None:
        """Create empty store."""
        self._sessions: Dict[str, Session] = {}

    def get(self, session_id: str) -> Optional[Session]:
        """Return session by id or None."""
        return self._sessions.get(session_id.strip())

    def create(self, attrs: Dict[str, Any]) -> Session:
        """Create session from attrs; id generated if not in attrs."""
        session = Session.create(
            model=attrs.get("model"),
            allowed_commands=attrs.get("allowed_commands"),
            forbidden_commands=attrs.get("forbidden_commands"),
            standards=attrs.get("standards"),
            session_rules=attrs.get("session_rules"),
            created_at=attrs.get("created_at"),
            session_id=attrs.get("id"),
            minimize_context=bool(attrs.get("minimize_context", False)),
        )
        self._sessions[session.id] = session
        return session

    def update(self, session_id: str, attrs: Dict[str, Any]) -> Session:
        """Update session; raises KeyError if not found."""
        sid = session_id.strip()
        if sid not in self._sessions:
            raise KeyError("Session not found: %s" % session_id)
        s = self._sessions[sid]
        allowed = attrs.get("allowed_commands")
        forbidden = attrs.get("forbidden_commands")
        standards = attrs.get("standards")
        session_rules = attrs.get("session_rules")
        new_s = Session(
            id=s.id,
            model=attrs.get("model") if "model" in attrs else s.model,
            allowed_commands=(
                tuple(allowed) if allowed is not None else s.allowed_commands
            ),
            forbidden_commands=(
                tuple(forbidden) if forbidden is not None else s.forbidden_commands
            ),
            standards=tuple(standards) if standards is not None else s.standards,
            session_rules=(
                tuple(session_rules) if session_rules is not None else s.session_rules
            ),
            created_at=s.created_at,
            minimize_context=(
                bool(attrs["minimize_context"])
                if "minimize_context" in attrs
                else s.minimize_context
            ),
        )
        self._sessions[sid] = new_s
        return new_s


class RedisSessionStore(SessionStore):
    """
    SessionStore backed by Redis. Key {key_prefix}:{session_id}, hash fields:
    model, allowed_commands, forbidden_commands, standards, session_rules,
    created_at, minimize_context (arrays as JSON; minimize_context "true"/"false").
    Standards and session_rules persisted.
    """

    def __init__(self, redis_client: Any, key_prefix: str = "session") -> None:
        """
        Initialize with Redis client and key prefix.
        Key for a session: {key_prefix}:{session_id}.
        """
        self._redis = redis_client
        self._prefix = (key_prefix or "session").strip() or "session"

    def _key(self, session_id: str) -> str:
        """Return Redis key for session_id."""
        return "%s:%s" % (self._prefix, session_id.strip())

    def get(self, session_id: str) -> Optional[Session]:
        """Return session by id or None if not found."""
        key = self._key(session_id)
        raw = self._redis.hgetall(key)
        if not raw:
            return None
        model = _decode_val(raw.get(_SESSION_FIELD_MODEL))
        allowed = _parse_list_json(raw.get(_SESSION_FIELD_ALLOWED))
        forbidden = _parse_list_json(raw.get(_SESSION_FIELD_FORBIDDEN))
        standards = _parse_list_json(raw.get(_SESSION_FIELD_STANDARDS))
        session_rules = _parse_list_json(raw.get(_SESSION_FIELD_SESSION_RULES))
        created_at = _decode_val(raw.get(_SESSION_FIELD_CREATED_AT))
        minimize_context = _parse_bool(raw.get(_SESSION_FIELD_MINIMIZE_CONTEXT))
        return Session(
            id=session_id.strip(),
            model=model,
            allowed_commands=tuple(allowed),
            forbidden_commands=tuple(forbidden),
            standards=tuple(standards),
            session_rules=tuple(session_rules),
            created_at=created_at,
            minimize_context=minimize_context,
        )

    def create(self, attrs: Dict[str, Any]) -> Session:
        """Create session and persist to Redis; id generated if not in attrs."""
        session = Session.create(
            model=attrs.get("model"),
            allowed_commands=attrs.get("allowed_commands"),
            forbidden_commands=attrs.get("forbidden_commands"),
            standards=attrs.get("standards"),
            session_rules=attrs.get("session_rules"),
            created_at=attrs.get("created_at"),
            session_id=attrs.get("id"),
            minimize_context=bool(attrs.get("minimize_context", False)),
        )
        key = self._key(session.id)
        mapping = {
            _SESSION_FIELD_MODEL: session.model or "",
            _SESSION_FIELD_ALLOWED: json.dumps(list(session.allowed_commands)),
            _SESSION_FIELD_FORBIDDEN: json.dumps(list(session.forbidden_commands)),
            _SESSION_FIELD_STANDARDS: json.dumps(list(session.standards)),
            _SESSION_FIELD_SESSION_RULES: json.dumps(list(session.session_rules)),
            _SESSION_FIELD_CREATED_AT: session.created_at or "",
            _SESSION_FIELD_MINIMIZE_CONTEXT: (
                "true" if session.minimize_context else "false"
            ),
        }
        self._redis.hset(key, mapping=mapping)
        return session

    def update(self, session_id: str, attrs: Dict[str, Any]) -> Session:
        """Update session in Redis; raises KeyError if not found."""
        existing = self.get(session_id)
        if existing is None:
            raise KeyError("Session not found: %s" % session_id)
        allowed = attrs.get("allowed_commands")
        forbidden = attrs.get("forbidden_commands")
        standards = attrs.get("standards")
        session_rules = attrs.get("session_rules")
        minimize_ctx = attrs.get("minimize_context")
        new_s = Session(
            id=existing.id,
            model=attrs.get("model") if "model" in attrs else existing.model,
            allowed_commands=(
                tuple(allowed) if allowed is not None else existing.allowed_commands
            ),
            forbidden_commands=(
                tuple(forbidden)
                if forbidden is not None
                else existing.forbidden_commands
            ),
            standards=tuple(standards) if standards is not None else existing.standards,
            session_rules=(
                tuple(session_rules)
                if session_rules is not None
                else existing.session_rules
            ),
            created_at=existing.created_at,
            minimize_context=(
                bool(minimize_ctx)
                if minimize_ctx is not None
                else existing.minimize_context
            ),
        )
        key = self._key(session_id)
        mapping = {
            _SESSION_FIELD_MODEL: new_s.model or "",
            _SESSION_FIELD_ALLOWED: json.dumps(list(new_s.allowed_commands)),
            _SESSION_FIELD_FORBIDDEN: json.dumps(list(new_s.forbidden_commands)),
            _SESSION_FIELD_STANDARDS: json.dumps(list(new_s.standards)),
            _SESSION_FIELD_SESSION_RULES: json.dumps(list(new_s.session_rules)),
            _SESSION_FIELD_CREATED_AT: new_s.created_at or "",
            _SESSION_FIELD_MINIMIZE_CONTEXT: (
                "true" if new_s.minimize_context else "false"
            ),
        }
        self._redis.hset(key, mapping=mapping)
        return new_s
