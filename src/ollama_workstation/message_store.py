"""
Message store abstraction for ContextBuilder: get_messages(session_id).
Closes 14_ambiguities #10b: we use MessageStore (not raw Redis client) so
context building is decoupled; default implementation is RedisMessageStore.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class MessageStore(ABC):
    """
    Abstraction for loading messages by session_id.
    ContextBuilder uses this (not Redis client directly); allows swapping storage.
    """

    @abstractmethod
    def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Return messages for session, ordered (e.g. by created_at).
        Each item: uuid, created_at, source, body, session_id (or role/content for API).
        """
        raise NotImplementedError


class RedisMessageStore(MessageStore):
    """
    MessageStore implementation using Redis. Reads keys {prefix}:* (e.g. message:uuid),
    filters by session_id, returns list ordered by created_at.
    """

    def __init__(self, redis_client: Any, key_prefix: str = "message") -> None:
        """Initialize with Redis client and key prefix (e.g. message)."""
        self._redis = redis_client
        self._prefix = (key_prefix or "message").strip().rstrip(":")

    def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """Load messages for session_id from Redis (scan keys, filter by session_id)."""
        pattern = "%s:*" % self._prefix
        out: List[Dict[str, Any]] = []
        for key in self._redis.scan_iter(match=pattern):
            data = self._redis.hgetall(key)
            if not data:
                continue
            if isinstance(key, bytes):
                key = key.decode("utf-8")
            msg = {}
            for k, v in (data or {}).items():
                if isinstance(k, bytes):
                    k = k.decode("utf-8")
                if isinstance(v, bytes):
                    v = v.decode("utf-8")
                msg[k] = v
            if msg.get("session_id") == session_id:
                out.append(msg)
        out.sort(key=lambda m: m.get("created_at") or "")
        return out
