"""
Context representation base: serialize tools and messages per provider.
Step 07.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class ContextRepresentation(ABC):
    """
    Abstract base: serialize tools and messages for a provider (Ollama, Gemini, etc.).
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

    def max_context_tokens(self, model_id: Optional[str] = None) -> Optional[int]:
        """
        Optional: max context window size for this representation/model.
        Returns None if not defined (caller uses config or other lookup).
        """
        return None
