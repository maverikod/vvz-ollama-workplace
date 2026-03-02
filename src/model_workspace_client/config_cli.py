"""
CLI for model workspace client config: generate, validate, show-schema, test-connection.

Client startup/init path must call validator before first network operation.
On validation errors at startup/init: return error and raise exception.
test-connection runs validation first then performs a real WS handshake in safe mode.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import argparse
import base64
import json
import os
import socket
import ssl
import sys
from pathlib import Path
from urllib.parse import urlparse

from model_workspace_client.config_generator import (
    _default_client_template,
    _env_overlay,
    generate_from_merged,
    merge_settings,
)
from model_workspace_client.config_validator import (
    ModelWorkspaceClientConfigError,
    validate_config,
)

# Exit codes for automation (stable).
EXIT_OK = 0
EXIT_VALIDATION_ERROR = 1
EXIT_CONFIG_ERROR = 2
EXIT_CONNECTION_ERROR = 3


def _parse_generate_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument(
        "--output",
        "-o",
        required=True,
        metavar="PATH",
        help="Output config file path.",
    )
    parser.add_argument(
        "--certs-dir",
        default=None,
        metavar="DIR",
        help="Dir with client/ca certs (default: CERTS_DIR or mtls_certificates).",
    )
    parser.add_argument(
        "--ws-endpoint",
        default="",
        metavar="URL",
        help="WebSocket endpoint (ws:// or wss://). Default: env or wss://...:8016.",
    )
    parser.add_argument(
        "--connect-timeout",
        type=int,
        default=30,
        metavar="SEC",
        help="Connect timeout in seconds (default: 30).",
    )
    parser.add_argument(
        "--request-timeout",
        type=int,
        default=120,
        metavar="SEC",
        help="Request timeout in seconds (default: 120).",
    )
    parser.add_argument(
        "--retry-max",
        type=int,
        default=3,
        metavar="N",
        help="Max retry attempts (default: 3).",
    )
    parser.add_argument(
        "--retry-backoff",
        type=float,
        default=2.0,
        metavar="SEC",
        help="Retry backoff seconds (default: 2.0).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Log level (default: INFO).",
    )
    parser.add_argument(
        "--metrics-enabled",
        action="store_true",
        help="Enable metrics in generated config.",
    )
    return parser


def _settings_from_generate_args(args: argparse.Namespace) -> dict:
    """Build generator settings from parsed generate args."""
    certs_dir = getattr(args, "certs_dir", None) or os.environ.get(
        "CERTS_DIR", "mtls_certificates"
    )
    certs_path = Path(certs_dir)
    tpl = _default_client_template(certs_path)
    env = _env_overlay()
    args_overlay: dict = {
        "output_path": str(Path(args.output).resolve()),
        "certs_dir": str(certs_path.resolve()),
        "ws_endpoint": (getattr(args, "ws_endpoint", None) or "").strip()
        or env.get("ws_endpoint")
        or tpl["ws_endpoint"],
        "connect_timeout_seconds": getattr(args, "connect_timeout", 30),
        "request_timeout_seconds": getattr(args, "request_timeout", 120),
        "retry_max_attempts": getattr(args, "retry_max", 3),
        "retry_backoff_seconds": getattr(args, "retry_backoff", 2.0),
        "log_level": getattr(args, "log_level", "INFO"),
        "metrics_enabled": getattr(args, "metrics_enabled", False),
    }
    return merge_settings(tpl, env, args_overlay)


def _cmd_generate(args: argparse.Namespace) -> int:
    """Generate client config from args and env."""
    settings = _settings_from_generate_args(args)
    generate_from_merged(args_overlay=settings)
    print(f"Wrote {settings['output_path']}", file=sys.stderr)
    return EXIT_OK


def _parse_validate_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument(
        "config",
        metavar="CONFIG",
        help="Path to client config JSON file to validate.",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Only exit code; do not print errors to stdout.",
    )
    return parser


def _cmd_validate(args: argparse.Namespace) -> int:
    """Validate config file; on errors print messages and return non-zero."""
    config_path = Path(args.config)
    try:
        validate_config(config_path)
    except ModelWorkspaceClientConfigError as e:
        if not getattr(args, "quiet", False):
            for msg in e.messages():
                print(msg, file=sys.stderr)
        return EXIT_VALIDATION_ERROR
    if not getattr(args, "quiet", False):
        print("Config is valid.", file=sys.stderr)
    return EXIT_OK


def _get_schema_doc() -> dict:
    """Return JSON-serializable schema description of client config."""
    return {
        "description": (
            "Model workspace client adapter config "
            "(adapter JSON with model_workspace_client and client sections)."
        ),
        "root": "JSON object",
        "sections": {
            "model_workspace_client": {
                "required": True,
                "fields": {
                    "ws_endpoint": "string, required, ws:// or wss:// URL",
                    "client_cert_file": "string, required for wss",
                    "client_key_file": "string, required for wss",
                    "ca_cert_file": "string, required for wss",
                    "connect_timeout_seconds": "integer, >= 1",
                    "request_timeout_seconds": "integer, >= 1",
                    "retry_max_attempts": "integer, >= 0",
                    "retry_backoff_seconds": "number, >= 0",
                    "observability": "object, optional (log_level, metrics_enabled)",
                },
            },
            "client": {
                "required_for_wss": True,
                "description": (
                    "When ws_endpoint is wss://, client.enabled=true and "
                    "client.protocol=mtls with client.ssl (cert, key, ca) required."
                ),
                "fields": {
                    "enabled": "boolean",
                    "protocol": "mtls",
                    "ssl": {"cert": "path", "key": "path", "ca": "path"},
                },
            },
        },
    }


def _parse_show_schema_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="json",
        help="Output format (default: json).",
    )
    return parser


def _cmd_show_schema(args: argparse.Namespace) -> int:
    """Print config schema to stdout."""
    schema = _get_schema_doc()
    if getattr(args, "format", "json") == "json":
        print(json.dumps(schema, indent=2))
    else:
        print("Model workspace client config schema:")
        print(json.dumps(schema, indent=2))
    return EXIT_OK


def _ws_handshake_safe(
    ws_endpoint: str,
    client_cert_file: str | None,
    client_key_file: str | None,
    ca_cert_file: str | None,
    timeout_seconds: int,
) -> tuple[bool, str]:
    """
    Real WebSocket HTTP upgrade handshake in safe mode (connect, handshake, close).

    Uses stdlib only: socket + ssl. Returns (success, message).
    """
    parsed = urlparse(ws_endpoint)
    scheme = (parsed.scheme or "ws").lower()
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if scheme == "wss" else 80)
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    try:
        if scheme == "wss":
            if not all([client_cert_file, client_key_file, ca_cert_file]):
                return (
                    False,
                    "wss requires client_cert_file, client_key_file, ca_cert_file",
                )
            assert (
                client_cert_file is not None
                and client_key_file is not None
                and ca_cert_file is not None
            )
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.load_verify_locations(ca_cert_file)
            ctx.load_cert_chain(certfile=client_cert_file, keyfile=client_key_file)
            sock = socket.create_connection((host, port), timeout=timeout_seconds)
            try:
                sock = ctx.wrap_socket(sock, server_hostname=host)
            except ssl.SSLError as e:
                sock.close()
                return (False, f"TLS handshake failed: {e}")
        else:
            sock = socket.create_connection((host, port), timeout=timeout_seconds)

        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        )
        sock.sendall(request.encode("utf-8"))
        buf = b""
        while b"\r\n\r\n" not in buf and len(buf) < 8192:
            chunk = sock.recv(4096)
            if not chunk:
                return (False, "Connection closed before handshake response")
            buf += chunk
        header_block = buf.split(b"\r\n\r\n", 1)[0].decode("utf-8", errors="replace")
        if "101" not in header_block.split("\r\n", 1)[0]:
            return (
                False,
                f"Expected 101 Switching Protocols; got: {header_block[:200]}",
            )
        return (True, "WebSocket handshake OK")
    except socket.timeout:
        return (False, f"Connection or handshake timeout ({timeout_seconds}s)")
    except (ConnectionRefusedError, OSError) as e:
        return (False, f"Connection failed: {e}")
    finally:
        try:
            sock.close()
        except (NameError, OSError):
            pass


def _parse_test_connection_args(
    parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    parser.add_argument(
        "config",
        metavar="CONFIG",
        help="Path to client config JSON file (validated before connection).",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Only exit code; minimal output.",
    )
    return parser


def _cmd_test_connection(args: argparse.Namespace) -> int:
    """
    Validate config then perform real WS handshake in safe mode.

    Client startup path: validator runs before first network operation.
    """
    config_path = Path(args.config)
    try:
        validate_config(config_path)
    except ModelWorkspaceClientConfigError as e:
        if not getattr(args, "quiet", False):
            for msg in e.messages():
                print(msg, file=sys.stderr)
        return EXIT_VALIDATION_ERROR

    with open(config_path, encoding="utf-8") as f:
        app_config = json.load(f)
    mwc = app_config.get("model_workspace_client") or {}
    ws_endpoint = (mwc.get("ws_endpoint") or "").strip()
    if not ws_endpoint:
        if not getattr(args, "quiet", False):
            print("model_workspace_client.ws_endpoint is missing", file=sys.stderr)
        return EXIT_CONFIG_ERROR

    timeout = int(mwc.get("connect_timeout_seconds", 30))
    ok, msg = _ws_handshake_safe(
        ws_endpoint,
        mwc.get("client_cert_file"),
        mwc.get("client_key_file"),
        mwc.get("ca_cert_file"),
        timeout,
    )
    if not ok:
        if not getattr(args, "quiet", False):
            print(f"test-connection failed: {msg}", file=sys.stderr)
        return EXIT_CONNECTION_ERROR
    if not getattr(args, "quiet", False):
        print("Connection OK.", file=sys.stderr)
    return EXIT_OK


def main() -> int:
    """Entry point: subcommands generate, validate, show-schema, test-connection."""
    top = argparse.ArgumentParser(
        prog="model-workspace-client-config-cli",
        description=(
            "Generate, validate, show-schema, or test-connection for "
            "model workspace client config (JSON)."
        ),
    )
    sub = top.add_subparsers(dest="command", required=True, help="Subcommand")

    gen = sub.add_parser(
        "generate", help="Generate client config from arguments and env."
    )
    _parse_generate_args(gen)
    gen.set_defaults(run=_cmd_generate)

    val = sub.add_parser("validate", help="Validate client config file.")
    _parse_validate_args(val)
    val.set_defaults(run=_cmd_validate)

    schema_parser = sub.add_parser(
        "show-schema",
        help="Print config schema (model_workspace_client and client sections).",
    )
    _parse_show_schema_args(schema_parser)
    schema_parser.set_defaults(run=_cmd_show_schema)

    test_conn = sub.add_parser(
        "test-connection",
        help="Validate config then perform WebSocket handshake (safe mode).",
    )
    _parse_test_connection_args(test_conn)
    test_conn.set_defaults(run=_cmd_test_connection)

    args = top.parse_args()
    return int(args.run(args))


if __name__ == "__main__":
    sys.exit(main())
