"""
Unit tests for MessageStreamWriter, RedisMessageRecord, MessageSource (step 09).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from ollama_workstation.message_source import MessageSource  # noqa: E402
from ollama_workstation.message_stream_writer import MessageStreamWriter  # noqa: E402
from ollama_workstation.redis_message_record import RedisMessageRecord  # noqa: E402


def test_record_source_enum_normalized() -> None:
    """RedisMessageRecord normalizes MessageSource to string."""
    r = RedisMessageRecord(
        uuid="u1",
        created_at="2025-01-01T00:00:00Z",
        source=MessageSource.USER,
        body="hi",
        session_id="s1",
    )
    assert r.source == "user"


def test_writer_write_calls_redis_hset() -> None:
    """write(record) calls redis.hset with key and mapping."""
    mock_redis = MagicMock()
    writer = MessageStreamWriter(mock_redis, key_prefix="msg")
    record = RedisMessageRecord(
        uuid="u1",
        created_at="2025-01-01T00:00:00Z",
        source="user",
        body="hello",
        session_id="s1",
    )
    writer.write(record)
    mock_redis.hset.assert_called_once()
    call = mock_redis.hset.call_args
    assert call[0][0] == "msg:u1"
    assert call[1]["mapping"]["uuid"] == "u1"
    assert call[1]["mapping"]["session_id"] == "s1"
    assert call[1]["mapping"]["body"] == "hello"


def test_writer_failure_logs_and_raises() -> None:
    """On Redis failure, writer logs and re-raises."""
    mock_redis = MagicMock()
    mock_redis.hset.side_effect = RuntimeError("connection refused")
    writer = MessageStreamWriter(mock_redis)
    record = RedisMessageRecord(
        uuid="u1",
        created_at="2025-01-01T00:00:00Z",
        source="user",
        body="x",
        session_id="s1",
    )
    with pytest.raises(RuntimeError, match="connection refused"):
        writer.write(record)
