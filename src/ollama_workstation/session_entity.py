"""
Session entity: id, model, allowed_commands, forbidden_commands, created_at.
Per plan §3.5.2; step 05.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Session:
    """
    Session for a dialogue: id (UUID4), model, allowed/forbidden commands.
    Model is required before context build (may be set at create or via update).
    """

    id: str
    model: Optional[str]
    allowed_commands: tuple[str, ...]
    forbidden_commands: tuple[str, ...]
    created_at: Optional[str] = None

    def __post_init__(self) -> None:
        """Ensure id is non-empty."""
        if not (self.id and self.id.strip()):
            raise ValueError("Session id is required")

    @classmethod
    def create(
        cls,
        model: Optional[str] = None,
        allowed_commands: Optional[List[str]] = None,
        forbidden_commands: Optional[List[str]] = None,
        created_at: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> "Session":
        """Build a new session with generated id (UUID4) unless session_id given."""
        sid = session_id or str(uuid.uuid4())
        return cls(
            id=sid,
            model=model,
            allowed_commands=tuple(allowed_commands or []),
            forbidden_commands=tuple(forbidden_commands or []),
            created_at=created_at,
        )
