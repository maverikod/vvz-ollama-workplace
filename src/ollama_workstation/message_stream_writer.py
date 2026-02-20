"""
Write RedisMessageRecord to Redis. Key layout: message:{uuid}; step 09.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import logging
from typing import Any

from .redis_message_record import RedisMessageRecord

logger = logging.getLogger(__name__)

# Key layout: primary key message:{uuid}; full message stored as hash or JSON.
# Secondary: list/set by session_id for listing (e.g. session:{session_id}:messages).
# TTL/retention: implementation-defined; document in deployment.


class MessageStreamWriter:
    """
    Writes RedisMessageRecord to Redis. Primary key by uuid; indices by session_id.
    On Redis failure: log and re-raise (no silent drop).
    """

    def __init__(
        self,
        redis_client: Any,
        key_prefix: str = "message",
    ) -> None:
        """
        Initialize with a Redis client (e.g. redis.Redis) and optional key prefix.
        """
        self._redis = redis_client
        self._prefix = (key_prefix or "message").strip().rstrip(":")

    def write(self, record: RedisMessageRecord) -> None:
        """
        Store record in Redis. Key = {prefix}:{uuid}; value = hash of fields.
        On failure: log and re-raise.
        """
        key = "%s:%s" % (self._prefix, record.uuid)
        mapping = {
            "uuid": record.uuid,
            "created_at": record.created_at,
            "source": record.source,
            "body": record.body,
            "session_id": record.session_id,
        }
        try:
            self._redis.hset(key, mapping=mapping)
        except Exception as e:  # noqa: BLE001
            logger.error(
                "MessageStreamWriter: failed to write message %s: %s",
                record.uuid,
                str(e),
            )
            raise
