"""
DocumentationSlotBuilder: fill doc block (canon first, then clarifications); step 11.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .documentation_source import DocumentationSource


class DocumentationSlotBuilder:
    """
    Fills the documentation slot: canon items first, then clarifications.
    Uses DocumentationSource; token budget from remainder_tokens.
    """

    def __init__(self, source: DocumentationSource) -> None:
        """Initialize with a DocumentationSource backend."""
        self._source = source

    def build(
        self,
        current_message: Dict[str, Any],
        session_id: Optional[str],
        remainder_tokens: int,
    ) -> List[Dict[str, Any]]:
        """
        Return ordered doc content segments (canon first, then clarifications).
        Stub: returns list of content blocks from source until budget used.
        """
        items = self._source.list_items(session_id)
        canon = [x for x in items if x.get("canon", True)]
        rest = [x for x in items if not x.get("canon", True)]
        ordered = canon + rest
        out: List[Dict[str, Any]] = []
        for item in ordered:
            text = self._source.get_content(item.get("id") or "")
            if text:
                out.append({"role": "user", "content": text})
        return out
