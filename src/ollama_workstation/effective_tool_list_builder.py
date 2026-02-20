"""
Effective tool list: merge config + session, resolve alias/safe name, build registry.
Step 06.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from .command_alias_registry import CommandAliasRegistry
from .command_discovery import parse_command_id
from .command_schema import CommandSchema
from .commands_policy_config import CommandsPolicyConfig
from .safe_name_translator import SafeNameTranslator
from .session_entity import Session
from .tool_call_registry import ToolCallRegistry

logger = logging.getLogger(__name__)

# Command IDs to always include when available (e.g. vectorization for RAG).
# Format: command_name.server_id (see command_discovery.make_command_id).
VECTORIZATION_COMMAND_IDS = (
    "embed_execute.embedding-service",
    "embed.embedding-service",
)


def build_effective_tool_list(
    session: Session,
    commands_policy_config: Optional[CommandsPolicyConfig],
    discovered_commands: List[Tuple[str, CommandSchema, bool]],
    alias_registry: CommandAliasRegistry,
    safe_name_translator: SafeNameTranslator,
) -> Tuple[List[Tuple[str, CommandSchema]], ToolCallRegistry]:
    """
    Merge config policy and session lists; resolve display name (alias or safe);
    build ToolCallRegistry. Returns (tool_list_canonical, registry).
    tool_list_canonical: list of (display_name, CommandSchema) for representation.
    """
    registry = ToolCallRegistry()
    used_display_names: set[str] = set()
    tool_list: List[Tuple[str, CommandSchema]] = []

    available = [(cid, schema) for cid, schema, avail in discovered_commands if avail]
    candidate_ids = [cid for cid, _ in available]
    id_to_schema = {cid: schema for cid, schema in available}

    if commands_policy_config is not None:
        candidate_ids = commands_policy_config.filter_candidates(candidate_ids)
    else:
        candidate_ids = list(candidate_ids)

    session_forbidden = set(session.forbidden_commands)
    session_allowed = (
        set(session.allowed_commands) if session.allowed_commands else None
    )
    effective_ids = [c for c in candidate_ids if c not in session_forbidden]
    if session_allowed is not None:
        effective_ids = [c for c in effective_ids if c in session_allowed]

    # Always add vectorization when available and not forbidden.
    effective_set = set(effective_ids)
    for vid in VECTORIZATION_COMMAND_IDS:
        if (
            vid not in session_forbidden
            and vid in id_to_schema
            and vid not in effective_set
        ):
            effective_ids.append(vid)
            effective_set.add(vid)

    model_id = session.model or ""

    for command_id in effective_ids:
        schema = id_to_schema.get(command_id)
        if schema is None:
            continue
        display_name = alias_registry.get_display_name(command_id, model_id)
        if display_name is None:
            display_name = safe_name_translator.to_safe_name(command_id)
        if display_name in used_display_names:
            logger.warning(
                "Duplicate display_name %s for command_id %s; using safe name",
                display_name,
                command_id,
            )
            display_name = safe_name_translator.to_safe_name(command_id)
        used_display_names.add(display_name)
        command_name, server_id = parse_command_id(command_id)
        registry.register(display_name, command_name, server_id)
        tool_list.append((display_name, schema))

    return (tool_list, registry)


class EffectiveToolListBuilder:
    """
    Builds effective tool list and ToolCallRegistry from session, policy, discovery.
    """

    def __init__(
        self,
        alias_registry: CommandAliasRegistry,
        safe_name_translator: SafeNameTranslator,
    ) -> None:
        """Initialize with alias registry and safe name translator."""
        self._alias_registry = alias_registry
        self._safe_name_translator = safe_name_translator

    def build(
        self,
        session: Session,
        commands_policy_config: Optional[CommandsPolicyConfig],
        discovered_commands: List[Tuple[str, CommandSchema, bool]],
    ) -> Tuple[List[Tuple[str, CommandSchema]], ToolCallRegistry]:
        """Return (tool_list_canonical, ToolCallRegistry) for the session."""
        return build_effective_tool_list(
            session=session,
            commands_policy_config=commands_policy_config,
            discovered_commands=discovered_commands,
            alias_registry=self._alias_registry,
            safe_name_translator=self._safe_name_translator,
        )
