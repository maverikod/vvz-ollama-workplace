"""
Registry: display_name -> (command_name, server_id) for resolving model tool calls.
Built when building effective tool list; used by chat flow; step 02.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from typing import Tuple


class ToolCallRegistry:
    """
    Mutable mapping display_name -> (command_name, server_id).
    Scope: per request or per session; built when building effective tool list.
    """

    def __init__(self) -> None:
        """Create an empty registry."""
        self._mapping: dict[str, Tuple[str, str]] = {}

    def register(
        self,
        display_name: str,
        command_name: str,
        server_id: str,
    ) -> None:
        """Register display_name -> (command_name, server_id)."""
        if not display_name.strip():
            raise ValueError("display_name must be non-empty")
        self._mapping[display_name.strip()] = (command_name, server_id)

    def resolve(self, display_name: str) -> Tuple[str, str]:
        """
        Return (command_name, server_id) for the given display_name.
        Raises KeyError if display_name was not registered.
        """
        key = display_name.strip()
        if key not in self._mapping:
            raise KeyError("Unknown tool name: %s" % display_name)
        return self._mapping[key]

    def __contains__(self, display_name: str) -> bool:
        """Return True if display_name is registered."""
        return display_name.strip() in self._mapping
