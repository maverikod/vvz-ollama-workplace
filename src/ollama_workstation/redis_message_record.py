"""
Redis message record: uuid, created_at, source, body, session_id.
Schema per plan §3.2a, §3.5.1; aligned with chunk_metadata_adapter; step 09.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from .message_source import MessageSource

# Schema (described structure per §3.2a):
# - uuid: string (UUID4), primary key; message id
# - created_at: string (ISO 8601 with timezone)
# - source: string (enum: user, model, tool, external_agent)
# - body: string (message content)
# - session_id: string (UUID4), mandatory for scope


@dataclass(frozen=True)
class RedisMessageRecord:
    """
    One message record for Redis. Primary key = uuid; by uuid full message assemblable.
    Field names aligned with chunk_metadata_adapter (SemanticChunk).
    """

    uuid: str
    created_at: str
    source: Union[str, MessageSource]
    body: str
    session_id: str

    def __post_init__(self) -> None:
        """Normalize source to string (enum value)."""
        src = self.source
        if isinstance(src, MessageSource):
            object.__setattr__(self, "source", src.value)
