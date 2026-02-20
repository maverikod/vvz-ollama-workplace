"""
SessionStore interface and in-memory implementation; step 05.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from .session_entity import Session


class SessionStore(ABC):
    """
    Persistence for Session: get, create, update.
    Config forbidden_commands is not stored here; applied in config layer (step 06).
    """

    @abstractmethod
    def get(self, session_id: str) -> Optional[Session]:
        """Return session by id or None if not found."""
        raise NotImplementedError

    @abstractmethod
    def create(self, attrs: Dict[str, Any]) -> Session:
        """Create session; attrs: model, allowed_commands, forbidden_commands."""
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
            created_at=attrs.get("created_at"),
            session_id=attrs.get("id"),
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
        new_s = Session(
            id=s.id,
            model=attrs.get("model") if "model" in attrs else s.model,
            allowed_commands=(
                tuple(allowed) if allowed is not None else s.allowed_commands
            ),
            forbidden_commands=(
                tuple(forbidden) if forbidden is not None else s.forbidden_commands
            ),
            created_at=s.created_at,
        )
        self._sessions[sid] = new_s
        return new_s
