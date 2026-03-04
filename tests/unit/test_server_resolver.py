"""
Unit tests for server_resolver: parse_server_url, get_server_url, embed config.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from ollama_workstation.config import WorkstationConfig  # noqa: E402
from ollama_workstation.commands_policy_config import (  # noqa: E402
    COMMANDS_POLICY_DENY_BY_DEFAULT,
    CommandsPolicyConfig,
)
from ollama_workstation.server_resolver import (  # noqa: E402
    _server_url_cache_from_list_servers,
    extract_servers_list,
    get_server_url,
    parse_server_url,
    server_url_to_embed_config_dict,
)


def test_parse_server_url_https_with_port() -> None:
    """parse_server_url extracts protocol, host, port from https URL."""
    out = parse_server_url("https://embedding-service:8008")
    assert out["protocol"] == "https"
    assert out["host"] == "embedding-service"
    assert out["port"] == 8008


def test_parse_server_url_http_default_port() -> None:
    """parse_server_url uses port 80 for http when missing."""
    out = parse_server_url("http://localhost")
    assert out["protocol"] == "http"
    assert out["host"] == "localhost"
    assert out["port"] == 80


def test_parse_server_url_empty_returns_defaults() -> None:
    """parse_server_url returns localhost:80 for empty string."""
    out = parse_server_url("")
    assert out["protocol"] == "http"
    assert out["host"] == "localhost"
    assert out["port"] == 80


def test_server_url_to_embed_config_dict_has_server_and_ssl() -> None:
    """server_url_to_embed_config_dict builds server section and ssl from config."""
    config = WorkstationConfig(
        mcp_proxy_url="https://p",
        ollama_base_url="http://o",
        ollama_model="m",
        proxy_client_cert="/path/cert",
        proxy_client_key="/path/key",
        proxy_ca_cert="/path/ca",
        commands_policy_config=CommandsPolicyConfig(
            allowed_commands=(),
            forbidden_commands=(),
            commands_policy=COMMANDS_POLICY_DENY_BY_DEFAULT,
        ),
    )
    out = server_url_to_embed_config_dict("https://embed:8008", config)
    assert out["server"]["base_url"] == "https://embed:8008"
    assert out["server"]["host"] == "embed"
    assert out["server"]["port"] == 8008
    assert out["ssl"]["enabled"] is True
    assert out["ssl"]["cert_file"] == "/path/cert"
    assert out["ssl"]["key_file"] == "/path/key"
    assert out["client"]["timeout"] == 60.0


@pytest.mark.asyncio
async def test_get_server_url_returns_url_when_in_list() -> None:
    """get_server_url returns server_url for server_id present in list_servers."""

    async def list_servers():
        return {
            "servers": [
                {"server_id": "embedding-service", "server_url": "https://emb:8008"},
            ],
        }

    url = await get_server_url(list_servers, "embedding-service")
    assert url == "https://emb:8008"


@pytest.mark.asyncio
async def test_get_server_url_returns_none_when_missing() -> None:
    """get_server_url returns None when server_id not in list."""

    async def list_servers():
        return {"servers": [{"server_id": "other", "server_url": "https://o:9"}]}

    url = await get_server_url(list_servers, "embedding-service")
    assert url is None


def test_extract_servers_list_nested_data() -> None:
    """extract_servers_list returns list from data.servers."""
    raw = {"data": {"servers": [{"server_id": "a", "server_url": "https://a:1"}]}}
    assert extract_servers_list(raw) == [
        {"server_id": "a", "server_url": "https://a:1"}
    ]


def test_extract_servers_list_flat() -> None:
    """extract_servers_list returns list from top-level servers."""
    raw = {"servers": [{"server_id": "b"}]}
    assert extract_servers_list(raw) == [{"server_id": "b"}]


def test_server_url_cache_from_list_servers_nested_data() -> None:
    """_server_url_cache_from_list_servers accepts nested data.servers (OpenAPI)."""
    raw = {
        "data": {
            "servers": [
                {"server_id": "embedding-service", "server_url": "https://emb:8008"},
            ],
        },
    }
    out = _server_url_cache_from_list_servers(raw)
    assert out.get("embedding-service") == "https://emb:8008"


def test_server_url_cache_from_list_servers_nested_result() -> None:
    """_server_url_cache_from_list_servers accepts nested result.servers (JSON-RPC)."""
    raw = {
        "result": {
            "servers": [
                {"server_id": "svo-chunker", "server_url": "https://svo:9000"},
            ],
        },
    }
    out = _server_url_cache_from_list_servers(raw)
    assert out.get("svo-chunker") == "https://svo:9000"


@pytest.mark.asyncio
async def test_get_server_url_with_nested_data() -> None:
    """get_server_url finds server when list_servers returns data.servers."""

    async def list_servers():
        return {
            "data": {
                "servers": [
                    {
                        "server_id": "embedding-service",
                        "server_url": "https://emb:8008",
                    },
                ],
            },
        }

    url = await get_server_url(list_servers, "embedding-service")
    assert url == "https://emb:8008"
