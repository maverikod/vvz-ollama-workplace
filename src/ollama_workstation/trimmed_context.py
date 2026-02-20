"""
TrimmedContext: ordered segments (standards, session_rules, N messages, relevance_slot).
Step 10.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class TrimmedContext:
    """
    Result of context build: ordered segments and optional token counts.
    """

    standards: List[Dict[str, Any]]
    session_rules: List[Dict[str, Any]]
    last_n_messages: List[Dict[str, Any]]
    relevance_slot_content: List[Dict[str, Any]]
    total_tokens_estimate: Optional[int] = None
