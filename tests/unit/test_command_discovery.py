"""
Unit tests for CommandDiscovery, make_command_id, parse_command_id (step 03).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from ollama_workstation.command_discovery import (  # noqa: E402
    CommandDiscovery,
    _commands_dict_to_list,
    make_command_id,
    parse_command_id,
)
from ollama_workstation.command_schema import CommandSchema  # noqa: E402
from ollama_workstation.config import WorkstationConfig  # noqa: E402
from ollama_workstation.proxy_client import ProxyClient  # noqa: E402


def test_make_command_id() -> None:
    """make_command_id builds name.server_id."""
    assert make_command_id("echo", "ollama-adapter") == "echo.ollama-adapter"


def test_parse_command_id() -> None:
    """parse_command_id splits on last dot."""
    assert parse_command_id("echo.ollama-adapter") == ("echo", "ollama-adapter")
    assert parse_command_id("a.b.c") == ("a.b", "c")


def _default_config() -> WorkstationConfig:
    from ollama_workstation.commands_policy_config import (
        COMMANDS_POLICY_DENY_BY_DEFAULT,
        CommandsPolicyConfig,
    )

    return WorkstationConfig(
        mcp_proxy_url="http://p",
        ollama_base_url="http://o",
        ollama_model="m",
        commands_policy_config=CommandsPolicyConfig(
            allowed_commands=(),
            forbidden_commands=(),
            commands_policy=COMMANDS_POLICY_DENY_BY_DEFAULT,
        ),
    )


async def test_refresh_builds_cache_from_list_servers() -> None:
    """refresh() builds cache from list_servers with servers[].commands."""
    config = _default_config()
    client = ProxyClient(config)
    client._call = AsyncMock(
        return_value={
            "servers": [
                {
                    "server_id": "s1",
                    "server_url": "https://s1.example/",
                    "commands": [
                        {
                            "name": "cmd1",
                            "description": "Desc1",
                            "parameters": {},
                        },
                    ],
                },
            ],
        }
    )
    discovery = CommandDiscovery(client, discovery_interval_sec=0)
    with patch.object(
        discovery, "_fetch_commands_from_server", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = [
            {"name": "cmd1", "description": "Desc1", "parameters": {}},
        ]
        await discovery.refresh()
    commands = discovery.get_discovered_commands()
    assert len(commands) == 1
    cid, schema, available = commands[0]
    assert cid == "cmd1.s1"
    assert schema.name == "cmd1"
    assert schema.description == "Desc1"
    assert available is True


def test_commands_dict_to_list() -> None:
    """_commands_dict_to_list converts proxy-style dict to list for _parse_command."""
    d = {
        "echo": {"summary": "Echo msg", "parameters": {"type": "object"}},
        "embed": {"summary": "Embed", "parameters": None},
    }
    out = _commands_dict_to_list(d)
    assert len(out) == 2
    names = {x["name"] for x in out}
    assert names == {"echo", "embed"}
    echo = next(x for x in out if x["name"] == "echo")
    assert echo["description"] == "Echo msg"
    assert echo["parameters"] == {"type": "object"}


async def test_refresh_uses_commands_from_proxy_when_dict() -> None:
    """refresh() uses server commands from proxy response when commands is a dict."""
    config = _default_config()
    client = ProxyClient(config)
    client._client = AsyncMock()
    client.list_servers = AsyncMock(
        return_value={
            "servers": [
                {
                    "server_id": "s1",
                    "server_url": "https://s1.example/",
                    "commands": {
                        "cmd_a": {"summary": "Desc A", "parameters": {}},
                        "cmd_b": {"summary": "Desc B", "parameters": {"x": {}}},
                    },
                },
            ],
        }
    )
    discovery = CommandDiscovery(client, discovery_interval_sec=0)
    await discovery.refresh()
    commands = discovery.get_discovered_commands()
    assert len(commands) == 2
    cids = {c[0] for c in commands}
    assert cids == {"cmd_a.s1", "cmd_b.s1"}


async def test_get_discovered_commands_available_only() -> None:
    """get_discovered_commands(available_only=True) filters out unavailable."""
    config = _default_config()
    client = ProxyClient(config)
    client._call = AsyncMock(return_value={"servers": []})
    discovery = CommandDiscovery(client)
    discovery._cache = [
        ("a.s1", CommandSchema("a", "A", {}), True),
        ("b.s1", CommandSchema("b", "B", {}), False),
    ]
    out = discovery.get_discovered_commands(available_only=True)
    assert len(out) == 1
    assert out[0][0] == "a.s1"
