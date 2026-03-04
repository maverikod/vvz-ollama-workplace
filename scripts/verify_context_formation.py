#!/usr/bin/env python3
"""
Verify context formation: Redis messages -> ContextBuilder -> serialized list.
Run from project root with .venv; set REDIS_PORT=63791 for test container.
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(PROJECT_ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

import redis

from ollama_workstation.context_builder import ContextBuilder, ContextBuilderError
from ollama_workstation.message_source import MessageSource
from ollama_workstation.message_store import RedisMessageStore
from ollama_workstation.message_stream_writer import MessageStreamWriter
from ollama_workstation.ollama_representation import OllamaRepresentation
from ollama_workstation.redis_message_record import RedisMessageRecord
from ollama_workstation.representation_registry import RepresentationRegistry
from ollama_workstation.relevance_slot_builder import RelevanceSlotBuilder
from ollama_workstation.session_store import InMemorySessionStore


async def main() -> int:
    host = os.environ.get("REDIS_HOST", "localhost")
    port = int(os.environ.get("REDIS_PORT", "63790"))
    prefix = os.environ.get("REDIS_KEY_PREFIX", "message")
    session_id = str(uuid.uuid4())

    print("Context formation check: Redis -> ContextBuilder -> serialized messages")
    print("  REDIS_HOST=%s REDIS_PORT=%s" % (host, port))

    try:
        client = redis.Redis(
            host=host,
            port=port,
            password=os.environ.get("REDIS_PASSWORD") or None,
            decode_responses=False,
        )
        client.ping()
    except Exception as e:
        print("  SKIP: Redis not available: %s" % e)
        return 0

    writer = MessageStreamWriter(client, key_prefix=prefix)
    store = RedisMessageStore(client, key_prefix=prefix)
    now = "2025-02-20T12:00:00Z"
    writer.write(
        RedisMessageRecord(
            uuid=str(uuid.uuid4()),
            created_at=now,
            source=MessageSource.USER,
            body="First user message",
            session_id=session_id,
        )
    )
    writer.write(
        RedisMessageRecord(
            uuid=str(uuid.uuid4()),
            created_at=now,
            source=MessageSource.MODEL,
            body="First model reply",
            session_id=session_id,
        )
    )

    session_store = InMemorySessionStore()
    session_store.create({"id": session_id, "model": "llama3.2"})
    registry = RepresentationRegistry(default=OllamaRepresentation())
    relevance_builder = RelevanceSlotBuilder(
        message_store=store,
        mode="fixed_order",
    )
    builder = ContextBuilder(
        session_store=session_store,
        representation_registry=registry,
        message_store=store,
        relevance_slot_builder=relevance_builder,
        model_context_tokens=4096,
    )
    current = {"role": "user", "content": "New user message"}
    try:
        trimmed, serialized = await builder.build(
            session_id=session_id,
            current_message=current,
            max_context_tokens=4096,
            last_n_messages=10,
            min_semantic_tokens=256,
            min_documentation_tokens=0,
            model_override="llama3.2",
        )
    except ContextBuilderError as e:
        print("  FAIL: ContextBuilder.build: %s" % e)
        return 1

    messages_for_chat = serialized + [current]
    if len(serialized) < 2:
        print(
            "  FAIL: expected serialized to contain 2 prior messages, got %s"
            % len(serialized)
        )
        return 1
    roles = [m.get("role") for m in serialized]
    if "user" not in roles or "model" not in roles:
        print("  FAIL: serialized should have user and model roles, got %s" % roles)
        return 1
    if messages_for_chat[-1] != current:
        print("  FAIL: last message should be current user message")
        return 1
    print(
        "  OK: ContextBuilder returned %s serialized + current -> %s messages"
        % (len(serialized), len(messages_for_chat))
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
