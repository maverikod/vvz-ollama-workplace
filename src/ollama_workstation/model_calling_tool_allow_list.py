"""
ModelCallingToolAllowList: which command_ids may trigger a model call; step 12.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from typing import Set


class ModelCallingToolAllowList:
    """
    Set of command_ids that are allowed to invoke the model (e.g. ollama_chat).
    Others execute as normal tools and do not push to call stack.
    """

    def __init__(self, command_ids: Set[str] | None = None) -> None:
        """Initialize with set of command_ids (e.g. {'ollama_chat.ollama-adapter'})."""
        self._allowed = set(command_ids or [])

    def may_call_model(self, command_id: str) -> bool:
        """Return True if this command_id may trigger a model invocation."""
        return (command_id or "").strip() in self._allowed

    def add(self, command_id: str) -> None:
        """Add command_id to the allow-list."""
        cid = (command_id or "").strip()
        if cid:
            self._allowed.add(cid)
