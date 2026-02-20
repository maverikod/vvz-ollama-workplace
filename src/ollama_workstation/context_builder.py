"""
ContextBuilder: load session, messages, trim, fill slots, serialize via representation.
Uses MessageStore (not raw Redis) for message source; closes #10b. Step 10.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .context_file_loader import load_text_file
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
        standards_file_path: Optional[str] = None,
        rules_file_path: Optional[str] = None,
    ) -> None:
        """Init with session store, registry, message store; optional file paths."""
        self._session_store = session_store
        self._representation_registry = representation_registry
        self._message_store = message_store
        self._relevance_slot_builder = relevance_slot_builder or RelevanceSlotBuilder()
        self._model_context_tokens = (
            model_context_tokens or DEFAULT_MODEL_CONTEXT_TOKENS
        )
        self._standards_file_path = (standards_file_path or "").strip() or None
        self._rules_file_path = (rules_file_path or "").strip() or None

    def build(
        self,
        session_id: str,
        current_message: Dict[str, Any],
        max_context_tokens: int,
        last_n_messages: int,
        min_semantic_tokens: int,
        min_documentation_tokens: int = 0,
        model_override: Optional[str] = None,
    ) -> tuple[TrimmedContext, List[Dict[str, Any]]]:
        """
        Load session and messages; apply order; trim; fill relevance slot; serialize.
        Returns (TrimmedContext, serialized_messages).
        model_override: use this for representation when session.model is not set.
        Raises ContextBuilderError if session missing or remainder too small.
        """
        session = self._session_store.get(session_id)
        if session is None:
            raise ContextBuilderError("Session not found: %s" % session_id)
        effective_model = (model_override or (session.model or "")).strip()
        if not effective_model:
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
        logger.debug(
            "context_build session_id=%s standards_count=%s session_rules_count=%s",
            session_id,
            len(session.standards),
            len(session.session_rules),
        )
        standards_list: List[str] = []
        if self._standards_file_path:
            file_standards = load_text_file(self._standards_file_path)
            if file_standards:
                standards_list.append(file_standards)
        standards_list.extend(session.standards)
        rules_list: List[str] = []
        if self._rules_file_path:
            file_rules = load_text_file(self._rules_file_path)
            if file_rules:
                rules_list.append(file_rules)
        rules_list.extend(session.session_rules)
        standards_blocks = [{"role": "system", "content": s} for s in standards_list]
        session_rules_blocks = [{"role": "system", "content": r} for r in rules_list]
        trimmed = TrimmedContext(
            standards=standards_blocks,
            session_rules=session_rules_blocks,
            last_n_messages=last_n,
            relevance_slot_content=relevance,
        )
        representation = self._representation_registry.get_representation(
            effective_model
        )
        ordered = (
            trimmed.standards
            + trimmed.session_rules
            + trimmed.last_n_messages
            + trimmed.relevance_slot_content
        )
        serialized = representation.serialize_messages(ordered)
        return (trimmed, serialized)
