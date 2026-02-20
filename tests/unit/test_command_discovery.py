"""
Unit tests for CommandDiscovery, make_command_id, parse_command_id (step 03).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from ollama_workstation.command_discovery import (  # noqa: E402
    CommandDiscovery,
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


async def test_refresh_builds_cache_from_list_servers() -> None:
    """refresh() builds cache from list_servers with servers[].commands."""
    config = WorkstationConfig(
        mcp_proxy_url="http://p",
        ollama_base_url="http://o",
        ollama_model="m",
    )
    client = ProxyClient(config)
    client._call = AsyncMock(
        return_value={
            "servers": [
                {
                    "server_id": "s1",
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
    await discovery.refresh()
    commands = discovery.get_discovered_commands()
    assert len(commands) == 1
    cid, schema, available = commands[0]
    assert cid == "cmd1.s1"
    assert schema.name == "cmd1"
    assert schema.description == "Desc1"
    assert available is True


async def test_get_discovered_commands_available_only() -> None:
    """get_discovered_commands(available_only=True) filters out unavailable."""
    config = WorkstationConfig(
        mcp_proxy_url="http://p",
        ollama_base_url="http://o",
        ollama_model="m",
    )
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
