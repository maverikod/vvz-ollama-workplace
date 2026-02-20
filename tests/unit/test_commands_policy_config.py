"""
Unit tests for CommandsPolicyConfig (step 01): filter_candidates, policy values.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from ollama_workstation.commands_policy_config import (  # noqa: E402
    COMMANDS_POLICY_ALLOW_BY_DEFAULT,
    COMMANDS_POLICY_DENY_BY_DEFAULT,
    CommandsPolicyConfig,
)


def test_deny_by_default_only_allowed_minus_forbidden() -> None:
    """deny_by_default: only candidates in allowed_commands and not in forbidden."""
    policy = CommandsPolicyConfig(
        allowed_commands=("a.x", "b.y"),
        forbidden_commands=("b.y",),
        commands_policy=COMMANDS_POLICY_DENY_BY_DEFAULT,
    )
    candidates = ["a.x", "b.y", "c.z"]
    assert policy.filter_candidates(candidates) == ["a.x"]


def test_allow_by_default_all_minus_forbidden() -> None:
    """allow_by_default with empty allowed: all candidates minus forbidden."""
    policy = CommandsPolicyConfig(
        allowed_commands=(),
        forbidden_commands=("b.y",),
        commands_policy=COMMANDS_POLICY_ALLOW_BY_DEFAULT,
    )
    candidates = ["a.x", "b.y", "c.z"]
    assert policy.filter_candidates(candidates) == ["a.x", "c.z"]


def test_allow_by_default_with_allowed_intersection() -> None:
    """allow_by_default with non-empty allowed: intersection then minus forbidden."""
    policy = CommandsPolicyConfig(
        allowed_commands=("a.x", "c.z"),
        forbidden_commands=(),
        commands_policy=COMMANDS_POLICY_ALLOW_BY_DEFAULT,
    )
    candidates = ["a.x", "b.y", "c.z"]
    assert policy.filter_candidates(candidates) == ["a.x", "c.z"]


def test_forbidden_always_excluded() -> None:
    """forbidden_commands always excluded regardless of policy."""
    policy = CommandsPolicyConfig(
        allowed_commands=("a.x", "b.y"),
        forbidden_commands=("a.x",),
        commands_policy=COMMANDS_POLICY_DENY_BY_DEFAULT,
    )
    candidates = ["a.x", "b.y"]
    assert policy.filter_candidates(candidates) == ["b.y"]


def test_invalid_policy_raises() -> None:
    """Invalid commands_policy value raises ValueError."""
    with pytest.raises(ValueError, match="commands_policy must be one of"):
        CommandsPolicyConfig(
            allowed_commands=(),
            forbidden_commands=(),
            commands_policy="invalid",
        )
