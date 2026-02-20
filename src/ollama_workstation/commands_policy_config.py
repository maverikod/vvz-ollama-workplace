"""
Commands policy configuration: allowed/forbidden commands and policy.
Loaded from config; consumed by EffectiveToolListBuilder (step 06).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

# allow_by_default: all discovered minus forbidden (optional allowed filter)
# deny_by_default: only allowed_commands minus forbidden_commands
COMMANDS_POLICY_ALLOW_BY_DEFAULT = "allow_by_default"
COMMANDS_POLICY_DENY_BY_DEFAULT = "deny_by_default"
COMMANDS_POLICY_VALUES = (
    COMMANDS_POLICY_ALLOW_BY_DEFAULT,
    COMMANDS_POLICY_DENY_BY_DEFAULT,
)


@dataclass(frozen=True)
class CommandsPolicyConfig:
    """
    Holds allowed_commands, forbidden_commands, and commands_policy.
    Used to filter the discovered command list for a session.
    """

    allowed_commands: tuple[str, ...]
    forbidden_commands: tuple[str, ...]
    commands_policy: str

    def __post_init__(self) -> None:
        """Validate commands_policy is one of the allowed values."""
        if self.commands_policy not in COMMANDS_POLICY_VALUES:
            raise ValueError(
                "commands_policy must be one of %s" % (COMMANDS_POLICY_VALUES,)
            )

    def filter_candidates(self, candidate_ids: List[str]) -> List[str]:
        """
        Apply policy and lists to a candidate set of command identifiers.
        forbidden_commands always take precedence (excluded regardless of policy).
        """
        forbidden_set = set(self.forbidden_commands)
        allowed_set = set(self.allowed_commands)
        candidates = [c for c in candidate_ids if c not in forbidden_set]
        if self.commands_policy == COMMANDS_POLICY_DENY_BY_DEFAULT:
            return [c for c in candidates if c in allowed_set]
        # allow_by_default: if allowed_commands non-empty, intersection
        if allowed_set:
            return [c for c in candidates if c in allowed_set]
        return candidates
