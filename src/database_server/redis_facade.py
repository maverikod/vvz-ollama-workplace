"""
Redis client facade for database-server adapter. Lazy client from config.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from typing import Any, Optional

_redis_client: Optional[Any] = None
_redis_config_key: Optional[tuple] = None


def get_redis_client(app_config: dict[str, Any]) -> Any:
    """
    Return Redis client for database_server.storage when backend is redis.

    Uses lazy singleton keyed by (host, port, password) so config changes
    (e.g. reload) get a new client. Returns None if backend is not redis
    or redis config is missing.
    """
    global _redis_client, _redis_config_key
    db = app_config.get("database_server") or {}
    storage = db.get("storage") or {}
    if storage.get("backend") != "redis":
        return None
    host = (storage.get("redis_host") or "localhost").strip()
    port = int(storage.get("redis_port", 6379))
    password = storage.get("redis_password")
    if password is not None:
        password = str(password).strip() or None
    key = (host, port, password)
    if _redis_client is not None and _redis_config_key == key:
        return _redis_client
    try:
        import redis
    except ImportError:
        return None
    _redis_client = redis.Redis(
        host=host,
        port=port,
        password=password,
        decode_responses=True,
    )
    _redis_config_key = key
    return _redis_client


def get_storage_prefixes(app_config: dict[str, Any]) -> tuple[str, str]:
    """
    Return (message_key_prefix, session_key_prefix) from database_server.storage.

    Defaults: ("message", "session"). Used when backend is redis.
    """
    db = app_config.get("database_server") or {}
    storage = db.get("storage") or {}
    msg = (storage.get("message_key_prefix") or "message").strip() or "message"
    sess = (storage.get("session_key_prefix") or "session").strip() or "session"
    return (msg.rstrip(":"), sess.rstrip(":"))
