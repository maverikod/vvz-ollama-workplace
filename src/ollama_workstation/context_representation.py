"""
Context representation base: serialize tools and messages per provider.
Step 07.

Adding a new model type = add one subclass of ContextRepresentation
(implement serialize_tools, serialize_messages, format_tool_result)
and register it in RepresentationRegistry for the model_id(s).
No changes to chat_flow or discovery.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class ContextRepresentation(ABC):
    """
    Abstract base for provider-specific context representation (Ollama, Gemini, etc.).
    Subclass once per model/API type; register in RepresentationRegistry.
    """

    @abstractmethod
    def serialize_tools(
        self,
        tool_list: List[tuple[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Convert canonical tool list (display_name, schema) to provider format.
        Returns list of tool definitions for the API.
        """
        raise NotImplementedError

    @abstractmethod
    def serialize_messages(
        self,
        messages: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Convert canonical messages (role, content, etc.) to provider format.
        Returns list of message objects for the API.
        """
        raise NotImplementedError

    @abstractmethod
    def format_tool_result(self, raw_result: Any) -> str:
        """
        Translate raw tool result (canonical layer output) to standard form
        for this provider (e.g. tool message content string the model sees).
        """
        raise NotImplementedError

    def max_context_tokens(self, model_id: Optional[str] = None) -> Optional[int]:
        """
        Optional: max context window size for this representation/model.
        Returns None if not defined (caller uses config or other lookup).
        """
        return None
