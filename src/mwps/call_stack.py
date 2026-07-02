"""
Call stack for model invocations triggered by tools; step 12.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from typing import List, Tuple


class CallStack:
    """
    Per-request stack of (tool_name, depth). Depth 0 = top-level chat.
    Push when entering model call from tool; pop when returning.
    """

    def __init__(self) -> None:
        """Create empty stack (depth 0)."""
        self._stack: List[Tuple[str, int]] = []

    def push(self, tool_name: str, depth: int) -> None:
        """Push frame (tool_name, depth)."""
        self._stack.append((tool_name, depth))

    def pop(self) -> None:
        """Pop the top frame."""
        if self._stack:
            self._stack.pop()

    def current_depth(self) -> int:
        """Return current depth (0 if stack empty)."""
        if not self._stack:
            return 0
        return self._stack[-1][1]
