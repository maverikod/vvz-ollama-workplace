"""
Unit tests for mwps-server config helper (base_url, timeout).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))  # noqa: E402
from mwps.mwps_server_config import (  # noqa: E402
    get_mwps_server_settings,
)


def test_get_mwps_server_settings_mwps_server_section() -> None:
    """base_url and timeout from mwps_server section."""
    config = {
        "mwps_server": {
            "base_url": "http://mwps:11434",
            "request_timeout_seconds": 30,
        },
    }
    base_url, timeout = get_mwps_server_settings(config)
    assert base_url == "http://mwps:11434"
    assert timeout == 30.0


def test_get_mwps_server_settings_mwps_fallback() -> None:
    """base_url from mwps.mwps when mwps_server missing."""
    config = {
        "mwps": {
            "mwps": {
                "base_url": "http://127.0.0.1:11434",
                "timeout": 120,
            },
        },
    }
    base_url, timeout = get_mwps_server_settings(config)
    assert base_url == "http://127.0.0.1:11434"
    assert timeout == 120.0


def test_get_mwps_server_settings_defaults() -> None:
    """Defaults when config empty or invalid."""
    base_url, timeout = get_mwps_server_settings(None)
    assert base_url == "http://127.0.0.1:11434"
    assert timeout == 60.0

    base_url2, timeout2 = get_mwps_server_settings({})
    assert base_url2 == "http://127.0.0.1:11434"
    assert timeout2 == 60.0


def test_get_mwps_server_settings_strips_trailing_slash() -> None:
    """base_url has no trailing slash."""
    config = {"mwps_server": {"base_url": "http://host:11434/"}}
    base_url, _ = get_mwps_server_settings(config)
    assert base_url == "http://host:11434"
