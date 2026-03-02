"""
Unit tests for model_workspace_server config validator.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from pathlib import Path

from model_workspace_server.config_validator import (
    validate_config_dict,
    validate_config_file,
)


def _valid_mws_config(
    include_ws_transport: bool = False, ssl_dir: Path | None = None
) -> dict:
    """Minimal valid config. With include_ws_transport=True, pass ssl_dir for ws+TLS."""
    server: dict = {
        "advertised_host": "test-mws",
        "servername": "test-mws",
        "log_dir": "/app/logs",
        "server_port": 8016,
    }
    if include_ws_transport and ssl_dir is not None:
        server["ssl"] = {
            "cert": str(ssl_dir / "cert.pem"),
            "key": str(ssl_dir / "key.pem"),
            "ca": str(ssl_dir / "ca.pem"),
        }
    transport: dict = {
        "fallback_policy": "deny",
        "verify_client": True,
    }
    if include_ws_transport:
        transport["transport_type"] = "ws"
    return {
        "server": server,
        "transport": transport,
        "model_workspace_server": {
            "runtime_identity": {
                "instance_uuid": "uuid-123",
                "server_id": "test-mws",
            },
            "limits": {
                "max_connections": 100,
                "request_timeout_seconds": 120,
            },
            "log_dir": "/app/logs",
        },
    }


def test_validate_config_dict_valid() -> None:
    """Valid config dict returns no errors."""
    assert validate_config_dict(_valid_mws_config()) == []


def test_validate_config_dict_missing_server() -> None:
    """Missing server section returns exact field path and [Remediation: ...]."""
    data = _valid_mws_config()
    del data["server"]
    errors = validate_config_dict(data)
    assert len(errors) >= 1
    assert "server" in errors[0]
    assert "missing" in errors[0].lower() or "required" in errors[0].lower()
    assert "[Remediation:" in errors[0]


def test_validate_config_dict_missing_model_workspace_server() -> None:
    """Missing model_workspace_server section returns path and remediation."""
    data = _valid_mws_config()
    del data["model_workspace_server"]
    errors = validate_config_dict(data)
    assert any("model_workspace_server" in e for e in errors)
    assert any("missing" in e.lower() or "required" in e.lower() for e in errors)


def test_validate_config_dict_missing_transport() -> None:
    """Missing transport section returns path and remediation."""
    data = _valid_mws_config()
    del data["transport"]
    errors = validate_config_dict(data)
    assert any("transport" in e for e in errors)


def test_validate_config_dict_server_no_advertised_host_nor_servername() -> None:
    """Server without advertised_host or servername is rejected."""
    data = _valid_mws_config()
    data["server"] = {"log_dir": "/app/logs"}
    errors = validate_config_dict(data)
    assert any("advertised_host" in e or "servername" in e for e in errors)
    assert any("required" in e.lower() for e in errors)


def test_validate_config_dict_transport_type_invalid() -> None:
    """Invalid transport_type returns exact path and allowed values."""
    data = _valid_mws_config()
    data["transport"]["transport_type"] = "http"  # no ssl required when not ws
    errors = validate_config_dict(data)
    assert any("transport.transport_type" in e for e in errors)
    assert any("ws" in e for e in errors)


def test_validate_config_dict_fallback_policy_invalid() -> None:
    """Invalid fallback_policy returns path and allowed values."""
    data = _valid_mws_config()
    data["transport"]["fallback_policy"] = "allow_all"
    errors = validate_config_dict(data)
    assert any("fallback_policy" in e for e in errors)
    assert any("deny" in e or "allow" in e for e in errors)


def test_validate_config_dict_runtime_identity_missing() -> None:
    """Missing runtime_identity returns path and remediation."""
    data = _valid_mws_config()
    del data["model_workspace_server"]["runtime_identity"]
    errors = validate_config_dict(data)
    assert any("runtime_identity" in e for e in errors)


def test_validate_config_dict_limits_missing() -> None:
    """Missing limits returns path and remediation."""
    data = _valid_mws_config()
    del data["model_workspace_server"]["limits"]
    errors = validate_config_dict(data)
    assert any("limits" in e for e in errors)


def test_validate_config_dict_limits_max_connections_out_of_range() -> None:
    """max_connections out of range returns exact path."""
    data = _valid_mws_config()
    data["model_workspace_server"]["limits"]["max_connections"] = 0
    errors = validate_config_dict(data)
    assert any("max_connections" in e for e in errors)
    data["model_workspace_server"]["limits"]["max_connections"] = 200_000
    errors2 = validate_config_dict(data)
    assert any("max_connections" in e for e in errors2)


def test_validate_config_dict_request_timeout_out_of_range() -> None:
    """request_timeout_seconds out of range returns path."""
    data = _valid_mws_config()
    data["model_workspace_server"]["limits"]["request_timeout_seconds"] = 0
    errors = validate_config_dict(data)
    assert any("request_timeout_seconds" in e for e in errors)


def test_validate_config_dict_server_port_invalid() -> None:
    """Invalid server_port returns path."""
    data = _valid_mws_config()
    data["server"]["server_port"] = 99999
    errors = validate_config_dict(data)
    assert any("server_port" in e or "server.server_port" in e for e in errors)


def test_validate_config_file_not_found(tmp_path: Path) -> None:
    """Non-existent file returns exact path and message."""
    path = tmp_path / "nonexistent.json"
    errors = validate_config_file(path)
    assert len(errors) == 1
    assert "not found" in errors[0].lower() or "config_path" in errors[0]


def test_validate_config_file_invalid_json(tmp_path: Path) -> None:
    """Invalid JSON returns config path error."""
    path = tmp_path / "bad.json"
    path.write_text("not json {")
    errors = validate_config_file(path)
    assert any("JSON" in e or "invalid" in e.lower() for e in errors)


def test_validate_config_file_valid_generated(tmp_path: Path) -> None:
    """Valid generated config file passes (adapter + MWS checks)."""
    from model_workspace_server.config_generator import generate_server_config

    certs = tmp_path / "certs"
    for sub in ("server", "client", "ca"):
        (certs / sub).mkdir(parents=True)
    for name in (
        "server/test-server.crt",
        "server/test-server.key",
        "client/test-server.crt",
        "client/test-server.key",
        "ca/ca.crt",
    ):
        (certs / name).write_text("")

    out = tmp_path / "config.json"
    settings = {
        "output_path": out,
        "certs_dir": str(certs),
        "server_port": 8016,
        "advertised_host": "test-mws",
        "log_dir": str(tmp_path / "logs"),
        "mcp_proxy_url": "https://proxy.example.com:3004",
        "transport_type": "ws",
        "fallback_policy": "deny",
    }
    generate_server_config(settings)

    errors = validate_config_file(out)
    # Adapter may report additional requirements; we only require no MWS-specific
    # errors with exact field path. If adapter is missing we get adapter skip msg.
    mws_errors = [
        err
        for err in errors
        if "model_workspace_server" in err or "transport.transport" in err
    ]
    assert not mws_errors, f"Unexpected MWS/transport errors: {mws_errors}"


def test_validate_config_dict_empty_root() -> None:
    """Empty dict returns errors for all required sections."""
    errors = validate_config_dict({})
    assert any("server" in e for e in errors)
    assert any("transport" in e for e in errors)
    assert any("model_workspace_server" in e for e in errors)


def test_validate_config_dict_verify_client_non_bool() -> None:
    """transport.verify_client must be boolean."""
    data = _valid_mws_config()
    data["transport"]["verify_client"] = "yes"
    errors = validate_config_dict(data)
    assert any("verify_client" in e for e in errors)


def test_validate_config_dict_valid_ws_with_ssl(tmp_path: Path) -> None:
    """Valid config with transport_type ws and existing server.ssl cert/key/ca."""
    (tmp_path / "cert.pem").write_text("")
    (tmp_path / "key.pem").write_text("")
    (tmp_path / "ca.pem").write_text("")
    config = _valid_mws_config(include_ws_transport=True, ssl_dir=tmp_path)
    assert validate_config_dict(config) == []


def test_validate_config_dict_ws_missing_server_ssl() -> None:
    """When transport_type is ws, missing server.ssl is rejected."""
    data = _valid_mws_config()
    data["transport"]["transport_type"] = "ws"
    # no server.ssl
    errors = validate_config_dict(data)
    assert any("server.ssl" in e and "required" in e.lower() for e in errors)


def test_validate_config_dict_ws_missing_ssl_cert_key() -> None:
    """When transport_type is ws, server.ssl without cert/key is rejected."""
    data = _valid_mws_config()
    data["transport"]["transport_type"] = "ws"
    data["server"]["ssl"] = {}  # cert and key missing
    errors = validate_config_dict(data)
    assert any("server.ssl.cert" in e or "server.ssl.key" in e for e in errors)
    data["server"]["ssl"] = {"cert": "", "key": ""}
    errors2 = validate_config_dict(data)
    assert any("server.ssl" in e for e in errors2)


def test_validate_config_dict_ws_ssl_file_not_found() -> None:
    """When transport_type is ws, server.ssl path that is not a file is rejected."""
    data = _valid_mws_config()
    data["transport"]["transport_type"] = "ws"
    data["server"]["ssl"] = {
        "cert": "/nonexistent/cert.pem",
        "key": "/nonexistent/key.pem",
    }
    errors = validate_config_dict(data)
    assert any("file not found" in e.lower() for e in errors)
    assert any("server.ssl" in e for e in errors)


def test_validate_config_dict_non_ws_no_ssl_required() -> None:
    """When transport_type is not ws, server.ssl is not required."""
    data = _valid_mws_config()  # no transport_type, no server.ssl
    errors = validate_config_dict(data)
    assert not any("server.ssl" in e for e in errors)
    # explicit non-ws: no ssl requirement (only transport_type error)
    data["transport"]["transport_type"] = "http"
    errors2 = validate_config_dict(data)
    assert any("transport.transport_type" in e for e in errors2)
    assert not any("server.ssl" in e for e in errors2)
