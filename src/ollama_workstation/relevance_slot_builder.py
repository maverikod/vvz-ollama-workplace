"""
Relevance slot: fixed-order (semantic then doc) for first impl; step 10.
Unified-by-relevance deferred until chunker and embed client available.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from typing import Any, Dict, List


class RelevanceSlotBuilder:
    """
    Fills the relevance slot. First implementation: fixed_order only
    (semantic then doc); returns [] until sources wired. Config: relevance_slot_mode.
    """

    def __init__(self, mode: str = "fixed_order") -> None:
        """Initialize with relevance_slot_mode (fixed_order or unified_by_relevance)."""
        self._mode = (mode or "fixed_order").strip() or "fixed_order"

    def fill_slot(
        self,
        current_message: Dict[str, Any],
        session_id: str,
        remainder_tokens: int,
    ) -> List[Dict[str, Any]]:
        """
        Return content for the relevance slot (fixed order: semantic then doc).
        Stub: returns [] until semantic search and DocumentationSource are wired.
        """
        return []
