#!/usr/bin/env python3
"""
Pipeline: verify Redis write/read/search using project modules.
Uses RedisMessageStore, MessageStreamWriter, RedisMessageRecord.
Connect to Redis at REDIS_HOST:REDIS_PORT (default localhost:63790 for host).
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timezone

# Project root and src on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(PROJECT_ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

import redis

from ollama_workstation.message_source import MessageSource
from ollama_workstation.message_store import RedisMessageStore
from ollama_workstation.message_stream_writer import MessageStreamWriter
from ollama_workstation.redis_message_record import RedisMessageRecord


def main() -> int:
    host = os.environ.get("REDIS_HOST", "localhost")
    port = int(os.environ.get("REDIS_PORT", "63790"))
    prefix = os.environ.get("REDIS_KEY_PREFIX", "message")
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    print("Block 1: Redis connection and write/read/search (project modules)")
    print("  REDIS_HOST=%s REDIS_PORT=%s prefix=%s" % (host, port, prefix))

    try:
        client = redis.Redis(
            host=host,
            port=port,
            password=os.environ.get("REDIS_PASSWORD") or None,
            decode_responses=False,
        )
        client.ping()
    except Exception as e:
        print("  FAIL: Redis connection: %s" % e, file=sys.stderr)
        return 1
    print("  OK: Redis connected")

    writer = MessageStreamWriter(client, key_prefix=prefix)
    store = RedisMessageStore(client, key_prefix=prefix)

    u1 = str(uuid.uuid4())
    u2 = str(uuid.uuid4())
    try:
        writer.write(
            RedisMessageRecord(
                uuid=u1,
                created_at=now,
                source=MessageSource.USER,
                body="Pipeline test user message",
                session_id=session_id,
            )
        )
        writer.write(
            RedisMessageRecord(
                uuid=u2,
                created_at=now,
                source=MessageSource.MODEL,
                body="Pipeline test model reply",
                session_id=session_id,
            )
        )
    except Exception as e:
        print("  FAIL: Write: %s" % e, file=sys.stderr)
        return 1
    print("  OK: Written 2 records (user + model) for session %s" % session_id)

    messages = store.get_messages(session_id)
    if len(messages) != 2:
        print(
            "  FAIL: Read by session_id: expected 2 messages, got %s" % len(messages),
            file=sys.stderr,
        )
        return 1
    bodies = [m.get("body") or "" for m in messages]
    if (
        "Pipeline test user message" not in bodies
        or "Pipeline test model reply" not in bodies
    ):
        print("  FAIL: Read: expected bodies not found", file=sys.stderr)
        return 1
    print("  OK: Read by session_id: got 2 messages")

    keys = list(client.scan_iter(match="%s:*" % prefix, count=100))
    if len(keys) < 2:
        print(
            "  FAIL: Search (scan keys): expected at least 2 keys, got %s" % len(keys),
            file=sys.stderr,
        )
        return 1
    print("  OK: Search (scan): found %s keys with prefix %s" % (len(keys), prefix))

    print("Block 1: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
