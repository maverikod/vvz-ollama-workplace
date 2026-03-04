"""
OLLAMA tool definitions: list_servers, call_server, help.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from typing import Any, Dict, List

# OLLAMA format: type "function", function: name, description, parameters (JSON Schema)


def _list_servers_parameters() -> Dict[str, Any]:
    """JSON Schema for list_servers parameters (page, page_size, filter_enabled)."""
    return {
        "type": "object",
        "properties": {
            "page": {
                "type": "integer",
                "description": "Page number (1-based). Omit for first page.",
            },
            "page_size": {
                "type": "integer",
                "description": "Servers per page. Omit for proxy default.",
            },
            "filter_enabled": {
                "type": "boolean",
                "description": "If true, only enabled servers. Omit for all.",
            },
        },
        "required": [],
    }


def _call_server_parameters() -> Dict[str, Any]:
    """JSON Schema for call_server (server_id, copy_number, command, params)."""
    return {
        "type": "object",
        "properties": {
            "server_id": {
                "type": "string",
                "description": "Server ID in the MCP Proxy (e.g. from list_servers).",
            },
            "copy_number": {
                "type": "integer",
                "description": "Server instance copy number; default 1.",
                "default": 1,
            },
            "command": {
                "type": "string",
                "description": "Command name (e.g. echo, help).",
            },
            "params": {
                "type": "object",
                "description": "Parameters for the command. Omit for no parameters.",
            },
        },
        "required": ["server_id", "command"],
    }


def _help_parameters() -> Dict[str, Any]:
    """JSON Schema for help parameters (server_id, copy_number, command)."""
    return {
        "type": "object",
        "properties": {
            "server_id": {
                "type": "string",
                "description": "Server ID to get help for (from list_servers).",
            },
            "copy_number": {
                "type": "integer",
                "description": "Server instance copy number; default 1.",
            },
            "command": {
                "type": "string",
                "description": "Optional command name for command-specific help.",
            },
        },
        "required": ["server_id"],
    }


def get_ollama_tools() -> List[Dict[str, Any]]:
    """
    Return the three mandatory tools in OLLAMA-compatible format.

    Each tool has type "function" and function with name, description, parameters.
    Used when building OLLAMA /api/chat requests.

    Returns:
        List of tool definitions for OLLAMA tools array.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "list_servers",
                "description": (
                    "List servers registered in the MCP Proxy. Use this to discover "
                    "available server_id values before calling call_server or help. "
                    "Supports optional pagination (page, page_size) and filter_enabled."
                ),
                "parameters": _list_servers_parameters(),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "call_server",
                "description": (
                    "Execute a command on a server registered in the MCP Proxy. "
                    "Requires server_id (from list_servers) and command name; optional "
                    "copy_number (default 1) and params object for the command."
                ),
                "parameters": _call_server_parameters(),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "help",
                "description": (
                    "Get help for a server or a command. Requires server_id; "
                    "optional copy_number and command."
                ),
                "parameters": _help_parameters(),
            },
        },
    ]


# Short reference (English) when help is called with no parameters.
HELP_REFERENCE_TEXT: str = """
How to use tools

1. You have a list of available tools. Each tool has a name, short description,
   and parameters (JSON Schema).

2. Calling a command: Invoke a tool by its name and pass a single "arguments"
   object (JSON) with the parameters required by that tool. The result is
   returned as tool message content (often JSON).

3. Help for a specific command: Call the "help" tool with parameter
   "command_name" set to the command name (e.g. "echo", "embed_execute",
   "ollama_chat") to get the full description and parameters from the server
   that provides that command.

4. This message: Call "help" with no parameters to see this reference again.
""".strip()

# Tool for model: always present. No params = short reference; command_name = full help.
MODEL_HELP_TOOL: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "help",
        "description": (
            "Without parameters: returns a short reference on how to use tools "
            "and how to call help for a specific command. With command_name: "
            "returns full description and parameters from the server that "
            "provides that command."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command_name": {
                    "type": "string",
                    "description": (
                        "Optional. Command name (e.g. echo, embed_execute) for "
                        "full help from its server. Omit for the short reference."
                    ),
                },
            },
            "required": [],
        },
    },
}
