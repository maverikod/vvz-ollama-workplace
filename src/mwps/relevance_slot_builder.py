"""
Relevance slot: gather blocks, sort by word overlap (non-vector ordering).
Trimming by token limit is applied after context creation (in ContextBuilder).

Vector/embedding-based ranking was removed; semantic vectorization is delegated
to external svo/embed services and is not called directly from mwps. Step 10.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from .documentation_source import DocumentationSource
from .message_store import MessageStore


def _word_set(text: str) -> Set[str]:
    """Lowercased non-empty words from text (for relevance scoring)."""
    if not text or not isinstance(text, str):
        return set()
    return {w.lower() for w in re.findall(r"\w+", text) if w}


def _word_relevance_score(query_words: Set[str], candidate_text: str) -> float:
    """Score candidate text vs query: overlap ratio (common / query size)."""
    if not query_words:
        return 0.0
    cand = _word_set(candidate_text)
    if not cand:
        return 0.0
    common = len(query_words & cand)
    return common / len(query_words)


class RelevanceSlotBuilder:
    """
    Fills the relevance slot: gather all relevant blocks, sort by word-overlap
    relevance. No token trimming here.
    """

    def __init__(
        self,
        message_store: Optional[MessageStore] = None,
        documentation_source: Optional[DocumentationSource] = None,
    ) -> None:
        """Init with optional message_store and documentation source."""
        self._message_store = message_store
        self._documentation_source = documentation_source

    def _gather_candidates(
        self,
        session_id: str,
        last_n_messages: int,
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """Return list of (text, block) for older messages + doc blocks."""
        out: List[Tuple[str, Dict[str, Any]]] = []
        if not self._message_store:
            return out
        messages = self._message_store.get_messages(session_id)
        n = max(0, last_n_messages)
        older = messages[:-n] if n else messages
        for m in older:
            body = (m.get("body") or "") if isinstance(m.get("body"), str) else ""
            role = (
                (m.get("source") or "user")
                if isinstance(m.get("source"), str)
                else "user"
            )
            block: Dict[str, Any] = {"role": role, "content": body}
            if body:
                out.append((body, block))
        if self._documentation_source:
            for item in self._documentation_source.list_items(session_id):
                item_id = item.get("id") or ""
                text = self._documentation_source.get_content(item_id)
                if text:
                    out.append((text, {"role": "user", "content": text}))
        return out

    async def fill_slot(
        self,
        current_message: Dict[str, Any],
        session_id: str,
        last_n_messages: int,
    ) -> List[Dict[str, Any]]:
        """
        Return relevance slot content: all relevant blocks sorted by
        word-overlap relevance to the current message.
        """
        query_text = (current_message.get("content") or "") if current_message else ""
        candidates = self._gather_candidates(session_id, last_n_messages)
        if not candidates:
            return []

        query_words = _word_set(query_text)
        scored = [
            (_word_relevance_score(query_words, text), block)
            for text, block in candidates
        ]
        scored.sort(key=lambda p: p[0], reverse=True)
        return [block for _s, block in scored]
