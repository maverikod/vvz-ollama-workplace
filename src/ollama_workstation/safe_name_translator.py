"""
Translate canonical command id to model-safe name (a-zA-Z0-9_ only).
Used when building effective tool list; step 02.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import re


def to_safe_name(command_id: str) -> str:
    """
    Produce a model-safe name from canonical command id (Command.ServerId).

    Replaces dot, space, hyphen with underscore; allows only [a-zA-Z0-9_].
    Collapses consecutive underscores to one.

    Examples:
        ollama_chat.ollama-adapter -> ollama_chat_ollama_adapter
        chunk.svo-chunker -> chunk_svo_chunker
    """
    if not command_id:
        return ""
    s = str(command_id).strip()
    for char in (".", " ", "-"):
        s = s.replace(char, "_")
    s = re.sub(r"[^a-zA-Z0-9_]", "", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


class SafeNameTranslator:
    """
    Translates canonical command ids to model-safe names.
    Idempotent: same command_id always yields the same safe name.
    """

    def to_safe_name(self, command_id: str) -> str:
        """Return model-safe name for the given command id."""
        return to_safe_name(command_id)
