"""
CLI for database client config: generate, validate, show-schema, test-connection.

Client startup/init must call validator before first network operation; on
validation errors the CLI returns non-zero and raises/prints errors.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from database_client.config_generator import (
    _default_client_template,
    _env_overlay,
    generate_from_merged,
)
from database_client.config_validator import (
    DatabaseClientConfigError,
    validate_config,
)


def _get_database_client_schema() -> dict[str, Any]:
    """Return JSON schema for database_client config (adapter + database_client)."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Database client adapter config",
        "description": "Adapter config with client and database_client (mTLS).",
        "type": "object",
        "required": ["database_client"],
        "properties": {
            "client": {
                "type": "object",
                "description": "Adapter client section (mTLS).",
                "properties": {
                    "enabled": {"type": "boolean"},
                    "protocol": {"type": "string", "enum": ["mtls"]},
                    "ssl": {
                        "type": "object",
                        "required": ["cert", "key", "ca"],
                        "properties": {
                            "cert": {
                                "type": "string",
                                "description": "Client cert file path",
                            },
                            "key": {
                                "type": "string",
                                "description": "Client key file path",
                            },
                            "ca": {
                                "type": "string",
                                "description": "CA cert file path",
                            },
                        },
                    },
                },
            },
            "database_client": {
                "type": "object",
                "description": "Database client endpoint and TLS/retry settings.",
                "required": [
                    "base_url",
                    "client_cert_file",
                    "client_key_file",
                    "ca_cert_file",
                ],
                "properties": {
                    "base_url": {
                        "type": "string",
                        "description": "Database server base URL (https).",
                    },
                    "client_cert_file": {"type": "string"},
                    "client_key_file": {"type": "string"},
                    "ca_cert_file": {"type": "string"},
                    "connect_timeout_seconds": {"type": "integer", "minimum": 1},
                    "request_timeout_seconds": {"type": "integer", "minimum": 1},
                    "retry_max_attempts": {"type": "integer", "minimum": 0},
                    "retry_backoff_seconds": {"type": "number", "minimum": 0},
                    "observability": {
                        "type": "object",
                        "properties": {
                            "log_level": {"type": "string"},
                            "metrics_enabled": {"type": "boolean"},
                        },
                    },
                },
            },
        },
    }


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
        default="mtls_certificates",
        metavar="DIR",
        help="Directory with client/ca certs (default: mtls_certificates).",
    )
    parser.add_argument(
        "--base-url",
        default="https://database-server:8017",
        metavar="URL",
        help="Database server base URL (default: %(default)s).",
    )
    parser.add_argument(
        "--connect-timeout",
        type=int,
        default=30,
        metavar="SEC",
        help="Connect timeout in seconds (default: %(default)s).",
    )
    parser.add_argument(
        "--request-timeout",
        type=int,
        default=120,
        metavar="SEC",
        help="Request timeout in seconds (default: %(default)s).",
    )
    parser.add_argument(
        "--retry-max-attempts",
        type=int,
        default=3,
        metavar="N",
        help="Max retry attempts (default: %(default)s).",
    )
    parser.add_argument(
        "--retry-backoff-seconds",
        type=float,
        default=2.0,
        metavar="SEC",
        help="Retry backoff in seconds (default: %(default)s).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        metavar="LEVEL",
        help="Log level (default: %(default)s).",
    )
    parser.add_argument(
        "--metrics-enabled",
        action="store_true",
        help="Enable metrics.",
    )
    return parser


def _args_overlay_from_namespace(args: argparse.Namespace) -> dict[str, Any]:
    """Build args overlay from parsed CLI namespace for generate_from_merged."""
    out_path = Path(args.output).resolve()
    certs_dir = Path(getattr(args, "certs_dir", "mtls_certificates")).resolve()
    overlay: dict[str, Any] = {
        "output_path": str(out_path),
        "certs_dir": str(certs_dir),
        "base_url": (getattr(args, "base_url", "") or "").strip().rstrip("/"),
        "connect_timeout_seconds": getattr(args, "connect_timeout", 30),
        "request_timeout_seconds": getattr(args, "request_timeout", 120),
        "retry_max_attempts": getattr(args, "retry_max_attempts", 3),
        "retry_backoff_seconds": getattr(args, "retry_backoff_seconds", 2.0),
        "log_level": getattr(args, "log_level", "INFO"),
        "metrics_enabled": getattr(args, "metrics_enabled", False),
    }
    return overlay


def _cmd_generate(args: argparse.Namespace) -> int:
    certs_dir = Path(getattr(args, "certs_dir", "mtls_certificates")).resolve()
    tpl = _default_client_template(certs_dir)
    args_overlay = _args_overlay_from_namespace(args)
    generate_from_merged(
        template=tpl, env_overlay=_env_overlay(), args_overlay=args_overlay
    )
    out_path = args_overlay.get("output_path", "config/database_client_config.json")
    print(f"Wrote {out_path}", file=sys.stderr)
    return 0


def _parse_validate_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument(
        "config",
        metavar="CONFIG",
        help="Path to database client config JSON file.",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Only exit code; do not print errors to stdout.",
    )
    return parser


def _cmd_validate(args: argparse.Namespace) -> int:
    config_path = Path(args.config)
    try:
        validate_config(config_path)
    except DatabaseClientConfigError as e:
        if not getattr(args, "quiet", False):
            for msg in e.messages():
                print(msg, file=sys.stderr)
        return 1
    if not getattr(args, "quiet", False):
        print("Config is valid.", file=sys.stderr)
    return 0


def _cmd_show_schema(_args: argparse.Namespace) -> int:
    print(json.dumps(_get_database_client_schema(), indent=2))
    return 0


def _test_connection_impl(config_path: Path) -> tuple[bool, str]:
    """
    Validate config then attempt HTTPS request with mTLS. Returns (success, message).
    Reports transport/auth failures clearly.
    """
    validate_config(config_path)
    with open(config_path, encoding="utf-8") as f:
        app_config = json.load(f)
    dbc = app_config.get("database_client")
    if not isinstance(dbc, dict):
        return (False, "database_client section missing or invalid")
    base_url = (dbc.get("base_url") or "").strip().rstrip("/")
    if not base_url:
        return (False, "database_client.base_url is empty")
    cert_file = dbc.get("client_cert_file") or ""
    key_file = dbc.get("client_key_file") or ""
    ca_file = dbc.get("ca_cert_file") or ""
    timeout_sec = int(dbc.get("connect_timeout_seconds", 30))
    if timeout_sec < 1:
        timeout_sec = 30

    try:
        import httpx
    except ImportError:
        return (False, "httpx not available; cannot run connection test")

    try:
        with httpx.Client(
            cert=(cert_file, key_file),
            verify=ca_file,
            timeout=timeout_sec,
        ) as client:
            resp = client.get(base_url)
    except httpx.ConnectError as e:
        return (False, f"Transport: connection failed: {e}")
    except httpx.TimeoutException as e:
        return (False, f"Transport: timeout after {timeout_sec}s: {e}")
    except httpx.ConnectTimeout as e:
        return (False, f"Transport: connect timeout: {e}")
    except Exception as e:
        err_str = str(e).lower()
        if "certificate" in err_str or "ssl" in err_str or "tls" in err_str:
            return (False, f"Auth/TLS: {e}")
        return (False, f"Connection error: {e}")

    if resp.status_code == 401:
        return (False, "Auth: server returned 401 Unauthorized")
    if resp.status_code == 403:
        return (False, "Auth: server returned 403 Forbidden")
    if resp.status_code >= 400:
        return (
            False,
            f"Server returned HTTP {resp.status_code}",
        )
    return (True, f"OK (HTTP {resp.status_code})")


def _parse_test_connection_args(
    parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    parser.add_argument(
        "--config",
        "-c",
        required=True,
        metavar="PATH",
        help="Path to database client config JSON file.",
    )
    return parser


def _cmd_test_connection(args: argparse.Namespace) -> int:
    config_path = Path(getattr(args, "config", ""))
    if not config_path.is_file():
        print(f"Error: config file not found: {config_path}", file=sys.stderr)
        return 1
    ok, msg = _test_connection_impl(config_path)
    if ok:
        print(msg, file=sys.stderr)
        return 0
    print(f"Connection test failed: {msg}", file=sys.stderr)
    return 1


def main() -> int:
    top = argparse.ArgumentParser(
        prog="database-client-config-cli",
        description=(
            "Generate, validate, show-schema, or test-connection for DB client config."
        ),
    )
    sub = top.add_subparsers(dest="command", required=True, help="Subcommand")

    gen = sub.add_parser(
        "generate", help="Generate database client config from arguments."
    )
    _parse_generate_args(gen)
    gen.set_defaults(run=_cmd_generate)

    val = sub.add_parser("validate", help="Validate database client config file.")
    _parse_validate_args(val)
    val.set_defaults(run=_cmd_validate)

    schema_parser = sub.add_parser(
        "show-schema", help="Print JSON schema for database client config."
    )
    schema_parser.set_defaults(run=_cmd_show_schema)

    test_conn = sub.add_parser(
        "test-connection",
        help="Validate config and test HTTPS/mTLS connection to database server.",
    )
    _parse_test_connection_args(test_conn)
    test_conn.set_defaults(run=_cmd_test_connection)

    args = top.parse_args()
    return int(args.run(args))


if __name__ == "__main__":
    sys.exit(main())
