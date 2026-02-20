"""
Unit tests for SafeNameTranslator and to_safe_name (step 02).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from ollama_workstation.safe_name_translator import (  # noqa: E402
    SafeNameTranslator,
    to_safe_name,
)


def test_ollama_chat_ollama_adapter() -> None:
    """ollama_chat.ollama-adapter -> ollama_chat_ollama_adapter."""
    assert to_safe_name("ollama_chat.ollama-adapter") == "ollama_chat_ollama_adapter"


def test_chunk_svo_chunker() -> None:
    """chunk.svo-chunker -> chunk_svo_chunker."""
    assert to_safe_name("chunk.svo-chunker") == "chunk_svo_chunker"


def test_class_to_safe_name() -> None:
    """SafeNameTranslator.to_safe_name same as module function."""
    t = SafeNameTranslator()
    assert t.to_safe_name("a.b-c") == "a_b_c"


def test_idempotent() -> None:
    """Same input yields same output."""
    cmd = "echo.my-server"
    assert to_safe_name(cmd) == to_safe_name(cmd)


def test_collapse_underscores() -> None:
    """Consecutive underscores collapsed to one."""
    assert to_safe_name("a..b--c  d") == "a_b_c_d"


def test_strip_non_alnum() -> None:
    """Non [a-zA-Z0-9_] removed."""
    assert "a" in to_safe_name("a@b#c")
    assert to_safe_name("a@b#c").replace("_", "") == "abc"
