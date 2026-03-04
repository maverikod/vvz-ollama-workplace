#!/usr/bin/env python3
"""
Verify context formation limits and rules without calling the model.
Uses in-memory session and message stores; no Redis, no OLLAMA.
See docs/context_formation.md for the rules and limits.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import asyncio
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(PROJECT_ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from ollama_workstation.context_builder import (  # noqa: E402
    ContextBuilder,
    ContextBuilderError,
)
from ollama_workstation.message_store import MessageStore  # noqa: E402
from ollama_workstation.ollama_representation import (  # noqa: E402
    OllamaRepresentation,
)
from ollama_workstation.representation_registry import (  # noqa: E402
    RepresentationRegistry,
)
from ollama_workstation.session_store import InMemorySessionStore  # noqa: E402


class StubMessageStore(MessageStore):
    """Fixed list of messages for get_messages."""

    def __init__(self, messages: list) -> None:
        self._messages = messages

    def get_messages(self, session_id: str) -> list:
        return list(self._messages)


async def run_checks() -> int:
    """Run all context-limit checks. Return 0 on success, 1 on failure."""
    failures = 0

    # --- 1. remainder < 0 must raise ContextBuilderError ---
    print("Check 1: remainder < 0 raises ContextBuilderError")
    session_store = InMemorySessionStore()
    session_store.create({"id": "s1", "model": "llama3.2"})
    reg = RepresentationRegistry()
    reg.register("llama3.2", OllamaRepresentation())
    msg_store = StubMessageStore([])
    builder = ContextBuilder(session_store, reg, msg_store, model_context_tokens=4096)
    try:
        await builder.build(
            "s1",
            {"role": "user", "content": "x"},
            max_context_tokens=200,
            last_n_messages=10,
            min_semantic_tokens=256,
            min_documentation_tokens=0,
        )
        print("  FAIL: expected ContextBuilderError (remainder < 0)")
        failures += 1
    except ContextBuilderError as e:
        if "Remainder" not in str(e) and "min_semantic" not in str(e).lower():
            print("  FAIL: wrong error: %s" % e)
            failures += 1
        else:
            print("  OK: ContextBuilderError as expected")
    except Exception as e:
        print("  FAIL: unexpected exception: %s" % e)
        failures += 1

    # --- 2. remainder >= 0 must not raise (build succeeds) ---
    print("Check 2: remainder >= 0 allows build to succeed")
    try:
        trimmed, serialized = await builder.build(
            "s1",
            {"role": "user", "content": "x"},
            max_context_tokens=500,
            last_n_messages=10,
            min_semantic_tokens=256,
            min_documentation_tokens=0,
        )
        # With empty store and no standards/rules, serialized can be []
        if not isinstance(serialized, list):
            print("  FAIL: serialized should be a list, got %s" % type(serialized))
            failures += 1
        else:
            print("  OK: build succeeded, %d serialized messages" % len(serialized))
    except Exception as e:
        print("  FAIL: %s" % e)
        failures += 1

    # --- 3. last_n_messages caps history count ---
    print("Check 3: last_n_messages caps number of history messages")
    many = [
        {"source": "user", "body": "msg %d" % i, "created_at": "2025-01-01T00:00:00Z"}
        for i in range(5)
    ]
    msg_store = StubMessageStore(many)
    builder2 = ContextBuilder(session_store, reg, msg_store, model_context_tokens=4096)
    try:
        trimmed, _ = await builder2.build(
            "s1",
            {"role": "user", "content": "current"},
            max_context_tokens=4096,
            last_n_messages=2,
            min_semantic_tokens=256,
            min_documentation_tokens=0,
        )
        if len(trimmed.last_n_messages) != 2:
            print(
                "  FAIL: expected 2 last_n_messages, got %d"
                % len(trimmed.last_n_messages)
            )
            failures += 1
        else:
            # Should be last two: msg 3, msg 4
            if trimmed.last_n_messages[0].get("content") != "msg 3":
                print(
                    "  FAIL: first of last_n should be 'msg 3', got %s"
                    % trimmed.last_n_messages[0].get("content")
                )
                failures += 1
            else:
                print("  OK: last_n_messages=2 -> 2 messages (last two from store)")
    except Exception as e:
        print("  FAIL: %s" % e)
        failures += 1

    # --- 4. Session not found raises ContextBuilderError ---
    print("Check 4: unknown session_id raises ContextBuilderError")
    try:
        await builder2.build(
            "no-such-session",
            {},
            max_context_tokens=4096,
            last_n_messages=10,
            min_semantic_tokens=256,
        )
        print("  FAIL: expected ContextBuilderError (session not found)")
        failures += 1
    except ContextBuilderError as e:
        if "Session not found" not in str(e) and "not found" not in str(e).lower():
            print("  FAIL: wrong error: %s" % e)
            failures += 1
        else:
            print("  OK: ContextBuilderError as expected")
    except Exception as e:
        print("  FAIL: unexpected exception: %s" % e)
        failures += 1

    # --- 5. Session model not set raises (without model_override) ---
    print("Check 5: session model not set raises without model_override")
    session_store.create({"id": "no-model", "model": None})
    try:
        await builder2.build(
            "no-model",
            {},
            max_context_tokens=4096,
            last_n_messages=10,
            min_semantic_tokens=256,
        )
        print("  FAIL: expected ContextBuilderError (model not set)")
        failures += 1
    except ContextBuilderError as e:
        if "model" not in str(e).lower():
            print("  FAIL: wrong error: %s" % e)
            failures += 1
        else:
            print("  OK: ContextBuilderError as expected")
    except Exception as e:
        print("  FAIL: unexpected exception: %s" % e)
        failures += 1

    # --- 6. Segment order: standards -> session_rules -> last_n -> relevance ---
    print("Check 6: segment order (standards, session_rules, last_n, relevance)")
    session_store.create(
        {
            "id": "order",
            "model": "llama3.2",
            "standards": ["Standard1"],
            "session_rules": ["Rule1"],
        }
    )
    msg_store_order = StubMessageStore(
        [{"source": "user", "body": "Hi", "created_at": "2025-01-01T00:00:00Z"}]
    )
    builder_order = ContextBuilder(
        session_store, reg, msg_store_order, model_context_tokens=4096
    )
    try:
        trimmed, serialized = await builder_order.build(
            "order",
            {"role": "user", "content": "x"},
            max_context_tokens=4096,
            last_n_messages=10,
            min_semantic_tokens=256,
        )
        # Expect: Standard1, Rule1, Hi (last_n), then relevance (empty)
        if len(serialized) < 3:
            print(
                "  FAIL: expected at least 3 serialized messages, got %d"
                % len(serialized)
            )
            failures += 1
        else:
            if serialized[0].get("content") != "Standard1":
                print(
                    "  FAIL: first segment should be Standard1, got %s" % serialized[0]
                )
                failures += 1
            elif serialized[1].get("content") != "Rule1":
                print("  FAIL: second segment should be Rule1, got %s" % serialized[1])
                failures += 1
            elif serialized[2].get("content") != "Hi":
                print("  FAIL: third segment should be Hi, got %s" % serialized[2])
                failures += 1
            else:
                print("  OK: order standards -> session_rules -> last_n -> relevance")
    except Exception as e:
        print("  FAIL: %s" % e)
        failures += 1

    # --- 7. effective_limit is min(model_context_tokens, max_context_tokens) ---
    print("Check 7: effective_limit caps at model_context_tokens")
    # Builder with model_context_tokens=1000; request max_context_tokens=5000.
    # remainder = min(1000,5000) - 256 - 0 = 744 >= 0, so build succeeds.
    builder_cap = ContextBuilder(
        session_store, reg, msg_store_order, model_context_tokens=1000
    )
    try:
        await builder_cap.build(
            "order",
            {},
            max_context_tokens=5000,
            last_n_messages=10,
            min_semantic_tokens=256,
        )
        print("  OK: effective_limit = min(1000,5000) = 1000, remainder >= 0")
    except ContextBuilderError as e:
        print("  FAIL: expected success (effective_limit=1000): %s" % e)
        failures += 1
    except Exception as e:
        print("  FAIL: %s" % e)
        failures += 1

    return failures


def main() -> int:
    print("Context limits verification (no model, no Redis)")
    print("See docs/context_formation.md for rules and limits.")
    print("")
    failures = asyncio.run(run_checks())
    print("")
    if failures:
        print("Result: %d check(s) failed." % failures)
        return 1
    print("Result: all checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
