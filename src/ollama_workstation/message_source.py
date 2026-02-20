"""
Message source enum: user, model, tool, external_agent.
Aligned with chunk_metadata_adapter SemanticChunk.source; step 09.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from enum import Enum


class MessageSource(str, Enum):
    """Who produced the message; aligned with SemanticChunk.source."""

    USER = "user"
    MODEL = "model"
    TOOL = "tool"
    EXTERNAL_AGENT = "external_agent"
