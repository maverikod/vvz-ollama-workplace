"""
ContextBuilder: load session, messages, trim, fill slots, serialize via representation.
Uses MessageStore (not raw Redis) for message source; closes #10b. Step 10.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .message_store import MessageStore
from .representation_registry import RepresentationRegistry
from .relevance_slot_builder import RelevanceSlotBuilder
from .session_store import SessionStore
from .trimmed_context import TrimmedContext

logger = logging.getLogger(__name__)

# Default model context window when not in config / API (step 10)
DEFAULT_MODEL_CONTEXT_TOKENS = 4096


class ContextBuilderError(Exception):
    """Raised when context build fails (session/model/remainder)."""

    pass


class ContextBuilder:
    """
    Builds model context: session, limit, messages, order, trim, serialize.
    Message source: MessageStore (get_messages); see message_store #10b.
    """

    def __init__(
        self,
        session_store: SessionStore,
        representation_registry: RepresentationRegistry,
        message_store: MessageStore,
        relevance_slot_builder: Optional[RelevanceSlotBuilder] = None,
        model_context_tokens: Optional[int] = None,
    ) -> None:
        """Initialize with session store, representation registry, message store."""
        self._session_store = session_store
        self._representation_registry = representation_registry
        self._message_store = message_store
        self._relevance_slot_builder = relevance_slot_builder or RelevanceSlotBuilder()
        self._model_context_tokens = (
            model_context_tokens or DEFAULT_MODEL_CONTEXT_TOKENS
        )

    def build(
        self,
        session_id: str,
        current_message: Dict[str, Any],
        max_context_tokens: int,
        last_n_messages: int,
        min_semantic_tokens: int,
        min_documentation_tokens: int = 0,
    ) -> tuple[TrimmedContext, List[Dict[str, Any]]]:
        """
        Load session and messages; apply order; trim; fill relevance slot; serialize.
        Returns (TrimmedContext, serialized_messages).
        Raises ContextBuilderError if session/model missing or remainder too small.
        """
        session = self._session_store.get(session_id)
        if session is None:
            raise ContextBuilderError("Session not found: %s" % session_id)
        if not session.model:
            raise ContextBuilderError(
                "Session model not set; set model via session update or init"
            )
        effective_limit = min(
            self._model_context_tokens,
            max(1, max_context_tokens),
        )
        messages = self._message_store.get_messages(session_id)
        last_n_raw = messages[-(last_n_messages):] if last_n_messages else []
        last_n = [
            {"role": m.get("source") or "user", "content": m.get("body") or ""}
            for m in last_n_raw
        ]
        remainder = effective_limit
        remainder -= min_semantic_tokens
        remainder -= min_documentation_tokens
        if remainder < 0:
            logger.error(
                "Context build: remainder < min_semantic_tokens (effective_limit=%s)",
                effective_limit,
            )
            raise ContextBuilderError(
                "Remainder < min_semantic_tokens; reduce last_n or increase limit"
            )
        relevance = self._relevance_slot_builder.fill_slot(
            current_message, session_id, remainder
        )
        trimmed = TrimmedContext(
            standards=[],
            session_rules=[],
            last_n_messages=last_n,
            relevance_slot_content=relevance,
        )
        representation = self._representation_registry.get_representation(session.model)
        ordered = (
            trimmed.standards
            + trimmed.session_rules
            + trimmed.last_n_messages
            + trimmed.relevance_slot_content
        )
        serialized = representation.serialize_messages(ordered)
        return (trimmed, serialized)
