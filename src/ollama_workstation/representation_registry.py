"""
Registry: model_id -> ContextRepresentation for provider-specific serialization.
Step 07. New model = new ContextRepresentation subclass + register(model_id, instance).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from typing import Dict, Optional, Type

from .context_representation import ContextRepresentation


class RepresentationRegistry:
    """
    Maps model_id to ContextRepresentation. Used to select the representation
    for the session's model; new model = register(model_id, subclass_instance).
    """

    def __init__(
        self,
        default: Optional[ContextRepresentation] = None,
    ) -> None:
        """
        Initialize registry with optional default for unknown model_id.
        """
        self._map: Dict[str, ContextRepresentation] = {}
        self._default = default

    def register(
        self,
        model_id: str,
        representation: ContextRepresentation,
    ) -> None:
        """Register representation for model_id."""
        self._map[model_id.strip()] = representation

    def register_type(
        self,
        model_id: str,
        representation_class: Type[ContextRepresentation],
    ) -> None:
        """Register representation class; instantiate on first get."""
        self._map[model_id.strip()] = representation_class()

    def get_representation(self, model_id: str) -> ContextRepresentation:
        """
        Return ContextRepresentation for model_id.
        If not found, return default or raise KeyError.
        """
        key = model_id.strip()
        if key in self._map:
            return self._map[key]
        if self._default is not None:
            return self._default
        raise KeyError("No representation registered for model: %s" % model_id)
