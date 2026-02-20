"""
Command schema: name, description, parameters (JSON Schema).
From proxy help/schema; step 03.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class CommandSchema:
    """
    Schema for one command: name, description, parameters (JSON Schema).
    From proxy list_servers or help(server_id, command).
    """

    name: str
    description: str
    parameters: Dict[str, Any]

    def __post_init__(self) -> None:
        """Ensure name and description are strings; parameters a dict."""
        if not isinstance(self.parameters, dict):
            raise ValueError("parameters must be a dict (JSON Schema)")
