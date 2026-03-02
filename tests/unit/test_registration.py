"""
Unit tests for command registration and command catalog normalization.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))  # noqa: E402
from ollama_workstation.registration import (  # noqa: E402
    _validate_registration_contract,
    register_ollama_workstation,
)


class _DummyRegistry:
    """Tiny registry stub for capturing command registration calls."""

    def __init__(self) -> None:
        self.calls: list[tuple[type, str]] = []

    def register(self, command_cls: type, section: str) -> None:
        self.calls.append((command_cls, section))


def test_register_ollama_workstation_registers_catalog_with_man_metadata() -> None:
    """All commands are registered and expose normalized metadata for help/discovery."""
    registry = _DummyRegistry()
    register_ollama_workstation(registry)

    assert len(registry.calls) == 11
    assert {section for _, section in registry.calls} == {"custom"}
    for command_cls, _ in registry.calls:
        meta = command_cls.get_metadata()  # type: ignore[attr-defined]
        assert meta["detail_level"] == "man"
        assert meta["params_schema"] == meta["params"] == meta["parameters"]
        if meta["params_schema"].get("type") == "object":
            assert meta["params_schema"]["additionalProperties"] is False


def test_validate_registration_contract_accepts_naming_freeze_shape() -> None:
    """mTLS contract from naming freeze passes strict registration validation."""
    config = {
        "ollama_workstation": {"mcp_proxy_url": "https://proxy.example.com:3004"},
        "registration": {
            "protocol": "mtls",
            "register_url": "https://proxy.example.com:3004/register",
            "unregister_url": "https://proxy.example.com:3004/unregister",
            "heartbeat": {"url": "https://proxy.example.com:3004/proxy/heartbeat"},
            "ssl": {
                "ca": "/app/mtls_certificates/ca/ca.crt",
                "cert": "/app/mtls_certificates/client/mcp-proxy.crt",
                "key": "/app/mtls_certificates/client/mcp-proxy.key",
            },
        },
        "server": {
            "ssl": {
                "cert": "/app/mtls_certificates/server/mcp-proxy.crt",
                "key": "/app/mtls_certificates/server/mcp-proxy.key",
            }
        },
    }
    _validate_registration_contract(config)


def test_validate_registration_contract_rejects_proxy_url_mismatch() -> None:
    """register_url must be derived from mcp_proxy_url from config."""
    config = {
        "ollama_workstation": {"mcp_proxy_url": "https://proxy.example.com:3004"},
        "registration": {
            "protocol": "mtls",
            "register_url": "https://other.example.com:3004/register",
            "unregister_url": "https://proxy.example.com:3004/unregister",
            "heartbeat": {"url": "https://proxy.example.com:3004/proxy/heartbeat"},
        },
    }
    with pytest.raises(ValueError, match="register_url"):
        _validate_registration_contract(config)
