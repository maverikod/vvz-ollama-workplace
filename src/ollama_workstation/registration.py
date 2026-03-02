"""
Register OLLAMA workstation command with the adapter registry.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Type

from .commands import (
    AddCommandToSessionCommand,
    DirectChatCommand,
    GetModelContextCommand,
    GetModelStateCommand,
    InvokeToolCommand,
    OllamaChatCommand,
    RemoveCommandFromSessionCommand,
    ServerStatusCommand,
    SessionInitCommand,
    SessionUpdateCommand,
    SetDefaultModelCommand,
)

_MAN_LEVEL = "man"
_REGISTER_PATH = "/register"
_UNREGISTER_PATH = "/unregister"
_HEARTBEAT_PATH = "/proxy/heartbeat"
_MTLS_CERTS_ROOT = "mtls_certificates/"
_MTLS_CA_SEGMENT = "mtls_certificates/ca/"
_MTLS_CLIENT_SEGMENT = "mtls_certificates/client/"
_MTLS_SERVER_SEGMENT = "mtls_certificates/server/"


def _normalize_path(value: Any) -> str:
    """Normalize config path to slash-separated string for substring checks."""
    return str(value or "").strip().replace("\\", "/")


def _ensure_object_schema(schema: Any) -> Dict[str, Any]:
    """
    Return strict object schema for command parameters.

    This keeps command discovery/help output deterministic for downstream clients.
    """
    if not isinstance(schema, dict):
        return {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        }
    out = dict(schema)
    if out.get("type") == "object" and "additionalProperties" not in out:
        out["additionalProperties"] = False
    return out


def _normalized_metadata(
    command_cls: Type[Any], raw: Mapping[str, Any]
) -> Dict[str, Any]:
    """Build metadata with unified schema keys and minimum detail level = man."""
    out: Dict[str, Any] = dict(raw or {})

    schema_fn = getattr(command_cls, "get_schema", None)
    schema_from_method = schema_fn() if callable(schema_fn) else {}
    params_schema = (
        out.get("params_schema")
        or out.get("params")
        or out.get("parameters")
        or schema_from_method
    )
    strict_schema = _ensure_object_schema(params_schema)
    out["params_schema"] = strict_schema
    out["params"] = strict_schema
    out["parameters"] = strict_schema
    out["detail_level"] = _MAN_LEVEL
    return out


def _wrap_metadata(command_cls: Type[Any]) -> None:
    """
    Patch get_metadata once so registry/help/discovery receive normalized shape.
    """
    if getattr(command_cls, "__ow_metadata_wrapped__", False):
        return
    original_meta = getattr(command_cls, "get_metadata", None)

    def _metadata_wrapper(cls: Type[Any]) -> Dict[str, Any]:
        raw_meta: Dict[str, Any] = {}
        if callable(original_meta):
            result = original_meta()
            if isinstance(result, dict):
                raw_meta = dict(result)
        return _normalized_metadata(cls, raw_meta)

    setattr(command_cls, "get_metadata", classmethod(_metadata_wrapper))
    setattr(command_cls, "__ow_metadata_wrapped__", True)


def _validate_registration_contract(config_data: Mapping[str, Any]) -> None:
    """Validate registration config against phase-1 naming freeze constraints."""
    registration = config_data.get("registration")
    if not isinstance(registration, Mapping):
        return

    protocol = str(registration.get("protocol") or "").strip().lower()
    if protocol != "mtls":
        raise ValueError('registration.protocol must be "mtls"')

    mcp_proxy_url = (
        str((config_data.get("ollama_workstation") or {}).get("mcp_proxy_url") or "")
        .strip()
        .rstrip("/")
    )
    register_url = str(registration.get("register_url") or "").strip()
    unregister_url = str(registration.get("unregister_url") or "").strip()
    heartbeat_url = str((registration.get("heartbeat") or {}).get("url") or "").strip()
    if mcp_proxy_url:
        if register_url != f"{mcp_proxy_url}{_REGISTER_PATH}":
            raise ValueError(
                "registration.register_url must match mcp_proxy_url/register"
            )
        if unregister_url != f"{mcp_proxy_url}{_UNREGISTER_PATH}":
            raise ValueError(
                "registration.unregister_url must match mcp_proxy_url/unregister"
            )
        if heartbeat_url != f"{mcp_proxy_url}{_HEARTBEAT_PATH}":
            raise ValueError(
                "registration.heartbeat.url must match mcp_proxy_url/proxy/heartbeat"
            )

    reg_ssl = registration.get("ssl") or {}
    server_ssl = (config_data.get("server") or {}).get("ssl") or {}
    ca_path = _normalize_path(reg_ssl.get("ca"))
    client_cert = _normalize_path(reg_ssl.get("cert"))
    client_key = _normalize_path(reg_ssl.get("key"))
    server_cert = _normalize_path(server_ssl.get("cert"))
    server_key = _normalize_path(server_ssl.get("key"))
    if _MTLS_CERTS_ROOT in "".join((ca_path, client_cert, client_key)):
        if _MTLS_CA_SEGMENT not in ca_path:
            raise ValueError("registration.ssl.ca must point to mtls_certificates/ca/")
        if (
            _MTLS_CLIENT_SEGMENT not in client_cert
            or _MTLS_CLIENT_SEGMENT not in client_key
        ):
            raise ValueError(
                "registration.ssl.cert/key must point to mtls_certificates/client/"
            )
    if _MTLS_CERTS_ROOT in "".join((server_cert, server_key)):
        if (
            _MTLS_SERVER_SEGMENT not in server_cert
            or _MTLS_SERVER_SEGMENT not in server_key
        ):
            raise ValueError(
                "server.ssl.cert/key must point to mtls_certificates/server/"
            )


def _command_classes() -> Iterable[Type[Any]]:
    """Return all workstation command classes included in command catalog."""
    return (
        OllamaChatCommand,
        ServerStatusCommand,
        SessionInitCommand,
        SessionUpdateCommand,
        AddCommandToSessionCommand,
        DirectChatCommand,
        RemoveCommandFromSessionCommand,
        GetModelContextCommand,
        GetModelStateCommand,
        InvokeToolCommand,
        SetDefaultModelCommand,
    )


def register_ollama_workstation(registry: Any) -> None:
    """
    Register OLLAMA workstation commands with the given adapter registry.

    Call this from the main app or a custom-commands hook so that
    ollama_chat, server_status, and session commands are available.

    Args:
        registry: CommandRegistry instance
        (e.g. from mcp_proxy_adapter.commands.command_registry).
    """
    # Validate registration endpoints/certs early when adapter config is available.
    cfg_data: Any = None
    try:
        from mcp_proxy_adapter.config import get_config

        cfg_data = getattr(get_config(), "config_data", None)
    except Exception:
        cfg_data = None
    if isinstance(cfg_data, Mapping):
        _validate_registration_contract(cfg_data)

    for command_cls in _command_classes():
        _wrap_metadata(command_cls)
        registry.register(command_cls, "custom")
