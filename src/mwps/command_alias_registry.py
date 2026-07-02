"""
Command alias registry: (command_id, model_id) -> display_name per model.
When building tool list, use alias if set else safe name; step 04.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple


class CommandAliasRegistry:
    """
    Mapping (command_id, model_id) -> display_name.
    get_display_name(command_id, model_id) returns None => use safe name (step 02).
    Alias unique per (session, model); duplicate handling at build time (step 06).
    """

    def __init__(
        self,
        aliases: Optional[Dict[Tuple[str, str], str]] = None,
    ) -> None:
        """
        Initialize with optional (command_id, model_id) -> display_name map.
        Default: empty, so all lookups return None (use safe name).
        """
        self._aliases: Dict[Tuple[str, str], str] = dict(aliases or {})

    def get_display_name(self, command_id: str, model_id: str) -> Optional[str]:
        """
        Return display name for (command_id, model_id), or None to use safe name.
        """
        key = (command_id.strip(), model_id.strip())
        return self._aliases.get(key)

    def set_alias(self, command_id: str, model_id: str, display_name: str) -> None:
        """Register alias for (command_id, model_id)."""
        key = (command_id.strip(), model_id.strip())
        self._aliases[key] = display_name.strip()
