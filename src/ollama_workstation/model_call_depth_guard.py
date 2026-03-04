"""
ModelCallDepthGuard: enforce max_model_call_depth before nested model call; step 12.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from .call_stack import CallStack


class ModelCallDepthGuard:
    """
    Before starting a model invocation from a tool: check current_depth < max.
    If depth exceeded, return error; otherwise allow and caller pushes.
    """

    def __init__(
        self,
        call_stack: CallStack,
        max_model_call_depth: int,
    ) -> None:
        """Initialize with call stack and max depth (e.g. 1 or 2)."""
        self._stack = call_stack
        self._max = max(0, max_model_call_depth)

    def can_enter_model_call(self) -> bool:
        """Return True if a nested model call is allowed (depth < max)."""
        return self._stack.current_depth() < self._max

    def error_if_over_depth(self) -> None:
        """Raise ValueError if current depth >= max (call before invoking model)."""
        if not self.can_enter_model_call():
            raise ValueError(
                "max recursion depth exceeded (max_model_call_depth=%s)" % self._max
            )
