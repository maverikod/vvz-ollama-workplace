"""
Unit tests for ollama-server config helper (base_url, timeout).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))  # noqa: E402
from ollama_workstation.ollama_server_config import (  # noqa: E402
    get_ollama_server_settings,
)


def test_get_ollama_server_settings_ollama_server_section() -> None:
    """base_url and timeout from ollama_server section."""
    config = {
        "ollama_server": {
            "base_url": "http://ollama:11434",
            "request_timeout_seconds": 30,
        },
    }
    base_url, timeout = get_ollama_server_settings(config)
    assert base_url == "http://ollama:11434"
    assert timeout == 30.0


def test_get_ollama_server_settings_ollama_workstation_fallback() -> None:
    """base_url from ollama_workstation.ollama when ollama_server missing."""
    config = {
        "ollama_workstation": {
            "ollama": {
                "base_url": "http://127.0.0.1:11434",
                "timeout": 120,
            },
        },
    }
    base_url, timeout = get_ollama_server_settings(config)
    assert base_url == "http://127.0.0.1:11434"
    assert timeout == 120.0


def test_get_ollama_server_settings_defaults() -> None:
    """Defaults when config empty or invalid."""
    base_url, timeout = get_ollama_server_settings(None)
    assert base_url == "http://127.0.0.1:11434"
    assert timeout == 60.0

    base_url2, timeout2 = get_ollama_server_settings({})
    assert base_url2 == "http://127.0.0.1:11434"
    assert timeout2 == 60.0


def test_get_ollama_server_settings_strips_trailing_slash() -> None:
    """base_url has no trailing slash."""
    config = {"ollama_server": {"base_url": "http://host:11434/"}}
    base_url, _ = get_ollama_server_settings(config)
    assert base_url == "http://host:11434"
