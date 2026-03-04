"""
Unit tests for EffectiveToolListBuilder (step 06).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from ollama_workstation.command_alias_registry import CommandAliasRegistry  # noqa: E402
from ollama_workstation.commands_policy_config import (  # noqa: E402
    COMMANDS_POLICY_ALLOW_BY_DEFAULT,
    CommandsPolicyConfig,
)
from ollama_workstation.effective_tool_list_builder import (  # noqa: E402
    EffectiveToolListBuilder,
    build_effective_tool_list,
)
from ollama_workstation.command_schema import CommandSchema  # noqa: E402
from ollama_workstation.session_entity import Session  # noqa: E402
from ollama_workstation.safe_name_translator import SafeNameTranslator  # noqa: E402


def test_build_effective_tool_list_config_forbidden_excluded() -> None:
    """Config forbidden_commands never appear in the list."""
    policy = CommandsPolicyConfig(
        allowed_commands=(),
        forbidden_commands=("forbidden.srv",),
        commands_policy=COMMANDS_POLICY_ALLOW_BY_DEFAULT,
    )
    session = Session.create(session_id="s1", model="m1")
    discovered = [
        ("ok.srv", CommandSchema("ok", "OK", {}), True),
        ("forbidden.srv", CommandSchema("forbidden", "No", {}), True),
    ]
    alias_reg = CommandAliasRegistry()
    safe = SafeNameTranslator()
    tools, reg = build_effective_tool_list(session, policy, discovered, alias_reg, safe)
    assert len(tools) == 1
    assert tools[0][0] == "ok"
    reg.resolve("ok")


def test_build_effective_tool_list_alias_used() -> None:
    """When alias is set, display_name is the alias and registered."""
    policy = CommandsPolicyConfig(
        allowed_commands=(),
        forbidden_commands=(),
        commands_policy=COMMANDS_POLICY_ALLOW_BY_DEFAULT,
    )
    session = Session.create(session_id="s1", model="m1")
    discovered = [
        ("echo.srv", CommandSchema("echo", "Echo", {}), True),
    ]
    alias_reg = CommandAliasRegistry()
    alias_reg.set_alias("echo.srv", "m1", "tool_echo")
    safe = SafeNameTranslator()
    tools, reg = build_effective_tool_list(session, policy, discovered, alias_reg, safe)
    assert len(tools) == 1
    assert tools[0][0] == "echo"
    assert reg.resolve("echo") == ("echo", "srv")


def test_builder_class_build() -> None:
    """EffectiveToolListBuilder.build same shape as build_effective_tool_list."""
    policy = CommandsPolicyConfig(
        allowed_commands=(),
        forbidden_commands=(),
        commands_policy=COMMANDS_POLICY_ALLOW_BY_DEFAULT,
    )
    session = Session.create(session_id="s1", model="m1")
    discovered = [
        ("a.b", CommandSchema("a", "A", {}), True),
    ]
    builder = EffectiveToolListBuilder(
        alias_registry=CommandAliasRegistry(),
        safe_name_translator=SafeNameTranslator(),
    )
    tools, reg = builder.build(session, policy, discovered)
    assert len(tools) == 1
    assert tools[0][0] == "a"
    assert reg.resolve("a") == ("a", "b")


def test_vectorization_added_when_available() -> None:
    """Vectorization commands are added when discovered and not forbidden."""
    policy = CommandsPolicyConfig(
        allowed_commands=(),
        forbidden_commands=(),
        commands_policy=COMMANDS_POLICY_ALLOW_BY_DEFAULT,
    )
    session = Session.create(session_id="s1", model="m1")
    embed_id = "embed_execute.embedding-service"
    discovered = [
        ("echo.srv", CommandSchema("echo", "Echo", {}), True),
        (embed_id, CommandSchema("embed_execute", "Embed", {}), True),
    ]
    alias_reg = CommandAliasRegistry()
    safe = SafeNameTranslator()
    tools, reg = build_effective_tool_list(session, policy, discovered, alias_reg, safe)
    display_names = [t[0] for t in tools]
    assert "echo" in display_names
    assert "embed_execute" in display_names
    resolved = reg.resolve("embed_execute")
    assert resolved == ("embed_execute", "embedding-service")


def test_vectorization_excluded_when_forbidden() -> None:
    """Vectorization command is not added when in session forbidden_commands."""
    policy = CommandsPolicyConfig(
        allowed_commands=(),
        forbidden_commands=(),
        commands_policy=COMMANDS_POLICY_ALLOW_BY_DEFAULT,
    )
    session = Session.create(
        session_id="s1",
        model="m1",
        forbidden_commands=["embed_execute.embedding-service"],
    )
    discovered = [
        (
            "embed_execute.embedding-service",
            CommandSchema("embed_execute", "E", {}),
            True,
        ),
    ]
    alias_reg = CommandAliasRegistry()
    safe = SafeNameTranslator()
    tools, _ = build_effective_tool_list(session, policy, discovered, alias_reg, safe)
    display_names = [t[0] for t in tools]
    assert "embed_execute_embedding_service" not in display_names
