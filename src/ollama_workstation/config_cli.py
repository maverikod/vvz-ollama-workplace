"""
CLI for adapter config generator and validator.
Subcommands: generate (write config from args), validate (check config file).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import argparse
import json
import sys
import uuid
from pathlib import Path

from ollama_workstation.config_generator_core import generate_adapter_config
from ollama_workstation.docker_config_validation import validate_project_config


def _comma_list(s: str) -> list[str]:
    """Parse comma-separated list; strip items; drop empty."""
    return [x.strip() for x in s.split(",") if x.strip()]


def _parse_generate_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument(
        "--output",
        "-o",
        required=True,
        metavar="PATH",
        help="Output config file path (e.g. config/adapter_config.json).",
    )
    parser.add_argument(
        "--certs-dir",
        default="/app/certs",
        metavar="DIR",
        help="Dir with server/client certs and keys (default: %(default)s).",
    )
    parser.add_argument(
        "--target",
        choices=("docker", "container"),
        default="docker",
        help="Preset: docker (8015) or container (8443). Default: %(default)s.",
    )
    parser.add_argument(
        "--server-port",
        type=int,
        metavar="PORT",
        help="Adapter port (default: 8015 docker, 8443 container).",
    )
    parser.add_argument(
        "--mcp-proxy-url",
        default="",
        metavar="URL",
        help=(
            "Full MCP proxy base URL, e.g. https://mcp-proxy:3004. "
            "If set, has priority over --mcp-proxy-host/--mcp-proxy-port."
        ),
    )
    parser.add_argument(
        "--mcp-proxy-host",
        default="mcp-proxy",
        metavar="HOST",
        help="MCP proxy host for registration (default: %(default)s).",
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
        metavar="HOST",
        help="Advertised server name (default by target: docker/container).",
    )
    parser.add_argument(
        "--log-dir",
        default="/app/logs",
        metavar="DIR",
        help="Server log directory (default: %(default)s).",
    )
    parser.add_argument(
        "--ollama-base-url",
        default="http://127.0.0.1:11434",
        metavar="URL",
        help="OLLAMA API base URL (default: %(default)s).",
    )
    parser.add_argument(
        "--ollama-model",
        default="llama3.2",
        metavar="NAME",
        help="Default OLLAMA model (default: %(default)s).",
    )
    parser.add_argument(
        "--ollama-models",
        default="llama3.2",
        metavar="LIST",
        help="Comma-separated ollama_models (default: --ollama-model value).",
    )
    parser.add_argument(
        "--redis-password",
        default=None,
        metavar="PASSWORD",
        help="Optional Redis password for ollama_workstation.",
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
        help="Registration server_id (default: advertised-host or ollama-workstation).",
    )
    # Optional ollama_workstation overrides
    parser.add_argument(
        "--ollama-timeout",
        type=int,
        default=60,
        metavar="SEC",
        help="OLLAMA request timeout in seconds (default: %(default)s).",
    )
    parser.add_argument(
        "--max-tool-rounds",
        type=int,
        default=10,
        metavar="N",
        help="Max tool-call rounds per request (default: %(default)s).",
    )
    parser.add_argument(
        "--commands-policy",
        choices=("allow_by_default", "deny_by_default"),
        default="allow_by_default",
        help="Command allow/deny policy (default: %(default)s).",
    )
    parser.add_argument(
        "--command-discovery-interval-sec",
        type=int,
        default=0,
        metavar="SEC",
        help="Command discovery interval, 0=disabled (default: %(default)s).",
    )
    parser.add_argument(
        "--session-store-type",
        default="memory",
        metavar="TYPE",
        help="Session store: memory or redis (default: %(default)s).",
    )
    parser.add_argument(
        "--redis-host",
        default="localhost",
        metavar="HOST",
        help="Redis host (default: %(default)s).",
    )
    parser.add_argument(
        "--redis-port",
        type=int,
        default=6379,
        metavar="PORT",
        help="Redis port (default: %(default)s).",
    )
    parser.add_argument(
        "--redis-key-prefix",
        default="message",
        metavar="PREFIX",
        help="Redis key prefix (default: %(default)s).",
    )
    parser.add_argument(
        "--max-context-tokens",
        type=int,
        default=4096,
        metavar="N",
        help="Max context tokens (default: %(default)s).",
    )
    parser.add_argument(
        "--last-n-messages",
        type=int,
        default=10,
        metavar="N",
        help="Last N messages in context (default: %(default)s).",
    )
    parser.add_argument(
        "--min-semantic-tokens",
        type=int,
        default=256,
        metavar="N",
        help="Min semantic tokens (default: %(default)s).",
    )
    parser.add_argument(
        "--min-documentation-tokens",
        type=int,
        default=0,
        metavar="N",
        help="Min documentation tokens (default: %(default)s).",
    )
    parser.add_argument(
        "--relevance-slot-mode",
        choices=("fixed_order", "unified_by_relevance"),
        default="fixed_order",
        help="Relevance slot mode (default: %(default)s).",
    )
    parser.add_argument(
        "--max-model-call-depth",
        type=int,
        default=1,
        metavar="N",
        help="Max model-call depth (default: %(default)s).",
    )
    parser.add_argument(
        "--allowed-commands",
        default="",
        metavar="LIST",
        help="Comma-separated allowed command names (default: empty).",
    )
    parser.add_argument(
        "--forbidden-commands",
        default="",
        metavar="LIST",
        help="Comma-separated forbidden command names (default: empty).",
    )
    parser.add_argument(
        "--model-calling-tool-allow-list",
        default="",
        metavar="LIST",
        help="Comma-separated tool names allowed for model calls (default: empty).",
    )
    return parser


def _settings_from_args(args: argparse.Namespace) -> dict:
    """Build generator settings dict from parsed args."""
    target = getattr(args, "target", "docker")
    if target == "container":
        default_port = 8443
        default_host = "ollama-workstation"
    else:
        default_port = 8015
        default_host = "ollama-adapter"

    server_port = getattr(args, "server_port", None) or default_port
    advertised_host = getattr(args, "advertised_host", None) or default_host
    ollama_models_str = getattr(args, "ollama_models", None) or getattr(
        args, "ollama_model", "llama3.2"
    )
    ollama_models = _comma_list(str(ollama_models_str) if ollama_models_str else "")

    settings: dict = {
        "output_path": Path(args.output).resolve(),
        "certs_dir": Path(args.certs_dir).resolve(),
        "server_port": server_port,
        "advertised_host": advertised_host,
        "log_dir": args.log_dir,
        "ollama_base_url": args.ollama_base_url,
        "ollama_model": args.ollama_model,
        "ollama_models": ollama_models,
        "redis_password": args.redis_password,
        "instance_uuid": args.instance_uuid or str(uuid.uuid4()),
        "registration_server_id": getattr(args, "registration_server_id", None),
        "ollama_timeout": args.ollama_timeout,
        "max_tool_rounds": args.max_tool_rounds,
        "commands_policy": args.commands_policy,
        "command_discovery_interval_sec": args.command_discovery_interval_sec,
        "session_store_type": args.session_store_type,
        "redis_host": args.redis_host,
        "redis_port": args.redis_port,
        "redis_key_prefix": args.redis_key_prefix,
        "max_context_tokens": args.max_context_tokens,
        "last_n_messages": args.last_n_messages,
        "min_semantic_tokens": args.min_semantic_tokens,
        "min_documentation_tokens": args.min_documentation_tokens,
        "relevance_slot_mode": args.relevance_slot_mode,
        "max_model_call_depth": args.max_model_call_depth,
        "allowed_commands": _comma_list(getattr(args, "allowed_commands", "") or ""),
        "forbidden_commands": _comma_list(
            getattr(args, "forbidden_commands", "") or ""
        ),
        "model_calling_tool_allow_list": _comma_list(
            getattr(args, "model_calling_tool_allow_list", "") or ""
        ),
    }
    proxy_url = (getattr(args, "mcp_proxy_url", "") or "").strip()
    if proxy_url:
        settings["mcp_proxy_url"] = proxy_url
    else:
        settings["mcp_proxy_host"] = args.mcp_proxy_host
        settings["mcp_proxy_port"] = args.mcp_proxy_port
    return settings


def _cmd_generate(args: argparse.Namespace) -> int:
    settings = _settings_from_args(args)
    generate_adapter_config(settings)
    print(f"Wrote {settings['output_path']}", file=sys.stderr)
    return 0


def _parse_validate_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument(
        "config",
        metavar="CONFIG",
        help="Path to adapter config JSON file to validate.",
    )
    parser.add_argument(
        "--no-adapter",
        action="store_true",
        help="Run only project-specific validation (skip mcp_proxy_adapter checks).",
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
    if not config_path.is_file():
        if not getattr(args, "quiet", False):
            print(f"Error: config file not found: {config_path}", file=sys.stderr)
        return 1
    try:
        app_config = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        if not getattr(args, "quiet", False):
            print(f"Error: invalid JSON: {e}", file=sys.stderr)
        return 1

    errors: list[str] = []

    if not getattr(args, "no_adapter", False):
        try:
            from mcp_proxy_adapter.core.config.simple_config import SimpleConfig
        except ImportError:
            if not getattr(args, "quiet", False):
                print(
                    "Warning: mcp_proxy_adapter not available; "
                    "skipping adapter validation.",
                    file=sys.stderr,
                )
        else:
            simple_config = SimpleConfig(str(config_path))
            simple_config.load()
            adapter_errors = simple_config.validate()
            for err in adapter_errors:
                errors.append(getattr(err, "message", str(err)))

    errors.extend(validate_project_config(app_config))

    if errors:
        if not getattr(args, "quiet", False):
            for msg in errors:
                print(msg, file=sys.stderr)
        return 1
    if not getattr(args, "quiet", False):
        print("Config is valid.", file=sys.stderr)
    return 0


def main() -> int:
    top = argparse.ArgumentParser(
        prog="config-cli",
        description="Generate or validate OLLAMA workstation adapter config (JSON).",
    )
    sub = top.add_subparsers(dest="command", required=True, help="Subcommand")

    gen_parser = sub.add_parser(
        "generate", help="Generate adapter config from arguments."
    )
    _parse_generate_args(gen_parser)
    gen_parser.set_defaults(run=_cmd_generate)

    val_parser = sub.add_parser(
        "validate",
        help="Validate adapter config file (project + optional adapter rules).",
    )
    _parse_validate_args(val_parser)
    val_parser.set_defaults(run=_cmd_validate)

    args = top.parse_args()
    return int(args.run(args))


if __name__ == "__main__":
    sys.exit(main())
