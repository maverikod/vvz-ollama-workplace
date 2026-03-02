"""
CLI for database server config: generate, validate, show-schema, sample.

Designed for prompt automation and CI. Startup path must call validator
before server run; on validation errors log structured errors and terminate.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from database_server.config_generator import generate_server_config
from database_server.config_validator import validate_config


def _sample_config_dict() -> dict[str, Any]:
    """
    Return a minimal valid database server config (structure only).

    Used by sample subcommand; paths are placeholders.
    """
    return {
        "server": {
            "host": "0.0.0.0",
            "port": 8017,
            "protocol": "mtls",
            "servername": "database-server",
            "advertised_host": "database-server",
            "ssl": {
                "cert": "/path/to/server.crt",
                "key": "/path/to/server.key",
                "ca": "/path/to/ca.crt",
            },
            "log_dir": "/app/logs",
        },
        "transport": {"verify_client": True},
        "database_server": {
            "auth": {"require_mtls": True},
            "storage": {"backend": "local", "data_dir": "/app/data"},
            "mount_paths": {
                "data_dir": "/app/data",
                "log_dir": "/app/logs",
                "certs_dir": "/path/to/certs",
            },
            "limits": {
                "max_connections": 100,
                "request_timeout_seconds": 120,
            },
            "runtime_identity": {
                "instance_uuid": "00000000-0000-0000-0000-000000000001",
                "server_id": "database-server",
            },
        },
    }


def _schema_text() -> str:
    """Return human-readable schema description for show-schema."""
    return """Database server config (JSON) schema:

Top-level:
  server (object, required)
    host, port (1-65535), protocol ("mtls"), servername, advertised_host (required)
    ssl (required when protocol=mtls): cert, key, ca (optional non-empty path)
    log_dir (optional, non-empty string)
  transport (object)
    verify_client (true when server.protocol is mtls)
  database_server (object, required)
    auth (object): require_mtls (true)
    storage (object, required): backend ("local"), data_dir (non-empty string)
    mount_paths (optional): data_dir, log_dir, certs_dir (non-empty strings)
    limits (optional): max_connections (>=1), request_timeout_seconds (>=1)
    runtime_identity (optional): instance_uuid, server_id (non-empty strings)

Adapter base (registration, etc.) is validated when --no-adapter is not set.
"""


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
        help="Directory with server/client certs (default: mtls_certificates).",
    )
    parser.add_argument(
        "--server-port",
        type=int,
        default=8017,
        metavar="PORT",
        help="Server listen port (default: 8017).",
    )
    parser.add_argument(
        "--mcp-proxy-url",
        default="",
        metavar="URL",
        help="MCP proxy base URL (overrides host/port if set).",
    )
    parser.add_argument(
        "--mcp-proxy-host",
        default="",
        metavar="HOST",
        help="MCP proxy host for registration.",
    )
    parser.add_argument(
        "--mcp-proxy-port",
        type=int,
        default=3004,
        metavar="PORT",
        help="MCP proxy port (default: 3004).",
    )
    parser.add_argument(
        "--advertised-host",
        default="database-server",
        metavar="HOST",
        help="Advertised server name (default: database-server).",
    )
    parser.add_argument(
        "--log-dir",
        default="/app/logs",
        metavar="DIR",
        help="Server log directory (default: /app/logs).",
    )
    parser.add_argument(
        "--data-dir",
        default="/app/data",
        metavar="DIR",
        help="Data directory (default: /app/data).",
    )
    parser.add_argument(
        "--verify-client",
        action="store_true",
        default=True,
        help="Require client mTLS (default: true).",
    )
    parser.add_argument(
        "--no-verify-client",
        action="store_false",
        dest="verify_client",
        help="Disable client certificate verification.",
    )
    parser.add_argument(
        "--storage-backend",
        choices=("local",),
        default="local",
        help="Storage backend (default: local).",
    )
    parser.add_argument(
        "--max-connections",
        type=int,
        default=100,
        metavar="N",
        help="Max connections (default: 100).",
    )
    parser.add_argument(
        "--request-timeout-seconds",
        type=int,
        default=120,
        metavar="SEC",
        help="Request timeout in seconds (default: 120).",
    )
    return parser


def _settings_from_generate_args(args: argparse.Namespace) -> dict[str, Any]:
    """Build generator settings from parsed generate args."""
    settings: dict[str, Any] = {
        "output_path": Path(args.output).resolve(),
        "certs_dir": str(Path(args.certs_dir).resolve()),
        "server_port": args.server_port,
        "advertised_host": args.advertised_host,
        "log_dir": args.log_dir,
        "data_dir": args.data_dir,
        "verify_client": args.verify_client,
        "storage_backend": args.storage_backend,
        "max_connections": args.max_connections,
        "request_timeout_seconds": args.request_timeout_seconds,
    }
    if getattr(args, "mcp_proxy_url", "").strip():
        settings["mcp_proxy_url"] = args.mcp_proxy_url.strip().rstrip("/")
    else:
        settings["registration_host"] = (
            getattr(args, "mcp_proxy_host", "") or "localhost"
        )
        settings["registration_port"] = getattr(args, "mcp_proxy_port", 3004)
    return settings


def _cmd_generate(args: argparse.Namespace) -> int:
    """Generate database server config file."""
    try:
        settings = _settings_from_generate_args(args)
        generate_server_config(settings)
        print("Generated: %s" % settings["output_path"], file=sys.stderr)
        return 0
    except ValueError as e:
        print("Error: %s" % e, file=sys.stderr)
        return 1


def _parse_validate_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument(
        "config",
        metavar="CONFIG",
        help="Path to database server config JSON.",
    )
    parser.add_argument(
        "--no-adapter",
        action="store_true",
        help="Skip adapter base validation (DB-server section only).",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Exit code only; do not print errors to stdout.",
    )
    return parser


def _cmd_validate(args: argparse.Namespace) -> int:
    """Validate config file; exit 1 on errors."""
    errors = validate_config(
        args.config,
        skip_adapter=getattr(args, "no_adapter", False),
    )
    if errors:
        if not getattr(args, "quiet", False):
            for msg in errors:
                print(msg, file=sys.stderr)
        return 1
    if not getattr(args, "quiet", False):
        print("Config is valid.", file=sys.stderr)
    return 0


def _cmd_show_schema(_args: argparse.Namespace) -> int:
    """Print config schema description."""
    print(_schema_text(), end="")
    return 0


def _cmd_sample(_args: argparse.Namespace) -> int:
    """Print sample config JSON to stdout."""
    print(json.dumps(_sample_config_dict(), indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    """Entry point for database server config CLI."""
    top = argparse.ArgumentParser(
        prog="database-server-config-cli",
        description="Generate, validate, show-schema, or sample DB server config.",
    )
    sub = top.add_subparsers(dest="command", required=True, help="Subcommand")

    gen = sub.add_parser("generate", help="Generate config from arguments.")
    _parse_generate_args(gen)
    gen.set_defaults(run=_cmd_generate)

    val = sub.add_parser("validate", help="Validate config file.")
    _parse_validate_args(val)
    val.set_defaults(run=_cmd_validate)

    sub.add_parser("show-schema", help="Print config schema description.").set_defaults(
        run=_cmd_show_schema
    )
    sub.add_parser("sample", help="Print sample config JSON to stdout.").set_defaults(
        run=_cmd_sample
    )

    args = top.parse_args()
    return int(args.run(args))


if __name__ == "__main__":
    sys.exit(main())
