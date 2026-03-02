"""
CLI for model workspace server config: generate, validate, show-schema, sample.

Stable exit codes for automation: 0 = success, 1 = failure.
Startup path should run validate before server; on validation errors log and exit.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import argparse
import json
import logging
import sys
import uuid
from pathlib import Path

from model_workspace_server.config_generator import (
    _default_template,
    generate_server_config,
    merge_settings,
)
from model_workspace_server.config_validator import validate_config_file

_LOG = logging.getLogger(__name__)

EXIT_SUCCESS = 0
EXIT_FAILURE = 1


def _build_sample_config() -> dict:
    """Build a minimal sample config dict (no file I/O) for show-sample."""
    return {
        "server": {
            "advertised_host": "model-workspace-server",
            "servername": "model-workspace-server",
            "server_port": 8016,
            "log_dir": "/app/logs",
            "ssl": {
                "cert": "/path/to/server.crt",
                "key": "/path/to/server.key",
                "ca": "/path/to/ca.crt",
            },
        },
        "transport": {
            "transport_type": "ws",
            "fallback_policy": "deny",
            "verify_client": True,
        },
        "model_workspace_server": {
            "runtime_identity": {
                "instance_uuid": str(uuid.uuid4()),
                "server_id": "model-workspace-server",
            },
            "limits": {
                "max_connections": 100,
                "request_timeout_seconds": 120,
            },
            "log_dir": "/app/logs",
        },
    }


def _build_schema_doc() -> dict:
    """Build a minimal schema description for show-schema (CI/prompt use)."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Model Workspace Server Config",
        "description": "Adapter config for model workspace server (WS, TLS).",
        "type": "object",
        "required": ["server", "transport", "model_workspace_server"],
        "properties": {
            "server": {
                "type": "object",
                "required": [],
                "description": (
                    "At least one of advertised_host or servername required."
                ),
                "properties": {
                    "advertised_host": {"type": "string"},
                    "servername": {"type": "string"},
                    "server_port": {"type": "integer", "minimum": 1, "maximum": 65535},
                    "log_dir": {"type": "string"},
                    "ssl": {
                        "type": "object",
                        "description": "Required when transport.transport_type is ws.",
                        "properties": {
                            "cert": {"type": "string"},
                            "key": {"type": "string"},
                            "ca": {"type": "string"},
                        },
                        "required": ["cert", "key"],
                    },
                },
            },
            "transport": {
                "type": "object",
                "properties": {
                    "transport_type": {"type": "string", "enum": ["ws"]},
                    "fallback_policy": {"type": "string", "enum": ["deny", "allow"]},
                    "verify_client": {"type": "boolean"},
                },
            },
            "model_workspace_server": {
                "type": "object",
                "required": ["runtime_identity", "limits"],
                "properties": {
                    "runtime_identity": {
                        "type": "object",
                        "required": ["instance_uuid", "server_id"],
                        "properties": {
                            "instance_uuid": {"type": "string"},
                            "server_id": {"type": "string"},
                        },
                    },
                    "limits": {
                        "type": "object",
                        "properties": {
                            "max_connections": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 100000,
                            },
                            "request_timeout_seconds": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 86400,
                            },
                        },
                    },
                    "log_dir": {"type": "string"},
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
        help="Directory with server/client certs (default: %(default)s).",
    )
    parser.add_argument(
        "--server-port",
        type=int,
        default=8016,
        metavar="PORT",
        help="Server port (default: %(default)s).",
    )
    parser.add_argument(
        "--mcp-proxy-url",
        default="",
        metavar="URL",
        help="MCP proxy base URL (e.g. https://proxy:3004). Overrides host/port.",
    )
    parser.add_argument(
        "--mcp-proxy-host",
        default="mcp-proxy",
        metavar="HOST",
        help="MCP proxy host (used if --mcp-proxy-url not set; default: %(default)s).",
    )
    parser.add_argument(
        "--mcp-proxy-port",
        type=int,
        default=3004,
        metavar="PORT",
        help="MCP proxy port (default: %(default)s).",
    )
    parser.add_argument(
        "--advertised-host",
        default="model-workspace-server",
        metavar="HOST",
        help="Advertised server name (default: %(default)s).",
    )
    parser.add_argument(
        "--log-dir",
        default="/app/logs",
        metavar="DIR",
        help="Log directory (default: %(default)s).",
    )
    parser.add_argument(
        "--instance-uuid",
        default=None,
        metavar="UUID",
        help="Registration instance UUID (default: random).",
    )
    parser.add_argument(
        "--registration-server-id",
        default=None,
        metavar="ID",
        help="Registration server_id (default: advertised-host).",
    )
    parser.add_argument(
        "--transport-type",
        choices=("ws",),
        default="ws",
        help="Transport type (default: %(default)s).",
    )
    parser.add_argument(
        "--fallback-policy",
        choices=("deny", "allow"),
        default="deny",
        help="Fallback policy (default: %(default)s).",
    )
    parser.add_argument(
        "--max-connections",
        type=int,
        default=100,
        metavar="N",
        help="Max connections (default: %(default)s).",
    )
    parser.add_argument(
        "--request-timeout-seconds",
        type=int,
        default=120,
        metavar="SEC",
        help="Request timeout in seconds (default: %(default)s).",
    )
    return parser


def _settings_from_generate_args(args: argparse.Namespace) -> dict:
    """Build generator settings from parsed generate args."""
    out_path = Path(args.output).resolve()
    certs_dir = Path(args.certs_dir).resolve()
    template = _default_template(certs_dir)
    args_overlay: dict = {
        "output_path": str(out_path),
        "certs_dir": str(certs_dir),
        "server_port": args.server_port,
        "advertised_host": args.advertised_host,
        "log_dir": args.log_dir,
        "transport_type": args.transport_type,
        "fallback_policy": args.fallback_policy,
        "max_connections": args.max_connections,
        "request_timeout_seconds": args.request_timeout_seconds,
    }
    if args.mcp_proxy_url:
        args_overlay["mcp_proxy_url"] = args.mcp_proxy_url.strip().rstrip("/")
    else:
        args_overlay["registration_host"] = args.mcp_proxy_host or "mcp-proxy"
        args_overlay["registration_port"] = args.mcp_proxy_port
    if args.instance_uuid:
        args_overlay["instance_uuid"] = args.instance_uuid
    if args.registration_server_id:
        args_overlay["registration_server_id"] = args.registration_server_id
    return merge_settings(template, None, args_overlay)


def _cmd_generate(args: argparse.Namespace) -> int:
    """Generate config file from arguments."""
    try:
        settings = _settings_from_generate_args(args)
        generate_server_config(settings)
    except (ValueError, OSError) as e:
        _LOG.error("generate failed: %s", e)
        print(f"Error: {e}", file=sys.stderr)
        return EXIT_FAILURE
    out_path = getattr(args, "output", "")
    print(f"Wrote {out_path}", file=sys.stderr)
    return EXIT_SUCCESS


def _parse_validate_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument(
        "config",
        metavar="CONFIG",
        help="Path to model workspace server config JSON.",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Only exit code; do not print errors to stdout.",
    )
    return parser


def _cmd_validate(args: argparse.Namespace) -> int:
    """Validate config file; on errors log diagnostics and return non-zero."""
    config_path = Path(args.config)
    errors = validate_config_file(config_path)
    if errors:
        if not getattr(args, "quiet", False):
            for msg in errors:
                print(msg, file=sys.stderr)
        for msg in errors:
            _LOG.warning("validation: %s", msg)
        return EXIT_FAILURE
    if not getattr(args, "quiet", False):
        print("Config is valid.", file=sys.stderr)
    return EXIT_SUCCESS


def _cmd_show_schema(_args: argparse.Namespace) -> int:
    """Print schema description (JSON) for CI and prompt-based workflows."""
    doc = _build_schema_doc()
    print(json.dumps(doc, indent=2))
    return EXIT_SUCCESS


def _cmd_sample(_args: argparse.Namespace) -> int:
    """Print a sample config JSON (no file I/O)."""
    sample = _build_sample_config()
    print(json.dumps(sample, indent=2))
    return EXIT_SUCCESS


def main() -> int:
    """Entry point: subcommands generate, validate, show-schema, sample."""
    top = argparse.ArgumentParser(
        prog="model-workspace-server-config",
        description="Generate or validate model workspace server config (JSON).",
    )
    sub = top.add_subparsers(dest="command", required=True, help="Subcommand")

    gen_parser = sub.add_parser("generate", help="Generate config from arguments.")
    _parse_generate_args(gen_parser)
    gen_parser.set_defaults(run=_cmd_generate)

    val_parser = sub.add_parser(
        "validate",
        help="Validate config file. Exit 0 if valid; else 1 and print errors.",
    )
    _parse_validate_args(val_parser)
    val_parser.set_defaults(run=_cmd_validate)

    schema_parser = sub.add_parser(
        "show-schema",
        help="Print JSON schema description for CI/prompt use.",
    )
    schema_parser.set_defaults(run=_cmd_show_schema)

    sample_parser = sub.add_parser(
        "sample",
        help="Print a sample config JSON to stdout.",
    )
    sample_parser.set_defaults(run=_cmd_sample)

    args = top.parse_args()
    return int(args.run(args))


if __name__ == "__main__":
    sys.exit(main())
