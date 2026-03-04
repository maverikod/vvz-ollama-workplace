"""
JSON schemas and metadata for the ollama_chat command.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from typing import Any, Dict


def get_ollama_chat_params_schema() -> Dict[str, Any]:
    """
    Get JSON schema for ollama_chat command parameters.

    Returns:
        JSON schema with descriptions and examples for parameters.
    """
    return {
        "type": "object",
        "properties": {
            "messages": {
                "type": "array",
                "description": (
                    "Chat messages in order. Each item must have 'role' "
                    "(e.g. 'user', 'assistant', 'system') and 'content'."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "role": {
                            "type": "string",
                            "description": "Role: user, assistant, or system",
                            "example": "user",
                        },
                        "content": {
                            "type": "string",
                            "description": "Message text content",
                            "example": "List available servers.",
                        },
                    },
                    "required": ["role", "content"],
                },
                "minItems": 1,
                "examples": [
                    [{"role": "user", "content": "Say hello."}],
                    [
                        {"role": "user", "content": "What can you do?"},
                        {"role": "assistant", "content": "I can list..."},
                        {"role": "user", "content": "Call list_servers."},
                    ],
                ],
            },
            "model": {
                "type": "string",
                "description": (
                    "OLLAMA model name. Overrides the default from config "
                    "(e.g. llama3.2, qwen3)."
                ),
                "example": "llama3.2",
            },
            "stream": {
                "type": "boolean",
                "description": (
                    "If true, response is streamed; if false, returns "
                    "full reply when done. Default: false."
                ),
                "default": False,
                "example": False,
            },
            "max_tool_rounds": {
                "type": "integer",
                "description": (
                    "Max tool-call rounds per request. Model can call "
                    "list_servers, call_server, help; each round may add "
                    "tool results. Overrides config if set. Must be >= 1."
                ),
                "minimum": 1,
                "example": 10,
            },
            "config_path": {
                "type": "string",
                "description": (
                    "Optional path to workstation config (YAML/JSON). "
                    "If omitted, adapter uses default path or env."
                ),
                "example": "/app/config/config.json",
            },
            "session_id": {
                "type": "string",
                "description": (
                    "Session UUID4 from session_init. When set together with "
                    "content, history is loaded from store (Redis), context "
                    "is built automatically, and the new user message and "
                    "assistant reply are persisted. Use either (messages) or "
                    "(session_id + content)."
                ),
            },
            "content": {
                "type": "string",
                "description": (
                    "New user message text. Required when session_id is set. "
                    "Appended to session history; then chat runs and reply "
                    "is saved to the session."
                ),
            },
        },
        "required": [],
        "additionalProperties": False,
        "example": {
            "session_id": "4d86c036-b5f0-435e-ac4b-f1f56d765769",
            "content": "What can you do?",
            "model": "llama3.2",
            "stream": False,
            "max_tool_rounds": 10,
        },
        "examples": [
            {
                "command": "ollama_chat",
                "params": {
                    "messages": [{"role": "user", "content": "List servers."}],
                },
                "description": "User message; model may call list_servers.",
            },
            {
                "command": "ollama_chat",
                "params": {
                    "session_id": "4d86c036-b5f0-435e-ac4b-f1f56d765769",
                    "content": "What can you do?",
                },
                "description": "By session: history loaded from store, reply saved.",
            },
        ],
        "description": (
            "Chat with OLLAMA; the model has access to MCP Proxy tools "
            "(list_servers, call_server, help). Returns the final assistant "
            "message and full message history."
        ),
    }


def get_ollama_chat_result_schema() -> Dict[str, Any]:
    """
    Get JSON schema for successful ollama_chat result.

    Returns:
        JSON schema describing the success response structure.
    """
    return {
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "const": True},
            "data": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Final assistant reply text",
                    },
                    "history": {
                        "type": "array",
                        "description": (
                            "Full message list including user, assistant, "
                            "and any tool-related messages."
                        ),
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string"},
                                "content": {"type": "string"},
                            },
                        },
                    },
                },
                "required": ["message", "history"],
            },
        },
        "required": ["success", "data"],
    }


def get_ollama_chat_error_schema() -> Dict[str, Any]:
    """
    Get JSON schema for ollama_chat error result.

    Returns:
        JSON schema describing the error response structure.
    """
    return {
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "const": False},
            "error": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "integer",
                        "description": "JSON-RPC error code",
                    },
                    "message": {
                        "type": "string",
                        "description": "Human-readable error message",
                    },
                    "data": {
                        "type": "object",
                        "description": "Optional extra error details",
                    },
                },
                "required": ["code", "message"],
            },
        },
        "required": ["success", "error"],
    }


def get_ollama_chat_metadata(name: str, description: str) -> Dict[str, Any]:
    """
    Build complete metadata for the ollama_chat command.

    Args:
        name: Command name.
        description: Command description (e.g. class docstring).

    Returns:
        Complete command metadata dictionary.
    """
    return {
        "name": name,
        "description": description,
        "params": get_ollama_chat_params_schema(),
        "result_schema": get_ollama_chat_result_schema(),
        "error_schema": get_ollama_chat_error_schema(),
        "error_codes": [
            {
                "code": -32602,
                "description": "Invalid parameters",
                "when": (
                    "Missing/invalid messages or config load failed "
                    "(e.g. mcp_proxy_url required)"
                ),
            },
            {
                "code": -32603,
                "description": "Internal error",
                "when": "Chat flow or OLLAMA/proxy communication failed",
            },
        ],
        "examples": {
            "success": {
                "success": True,
                "data": {
                    "message": "Here are the registered servers: ...",
                    "history": [
                        {"role": "user", "content": "List servers."},
                        {
                            "role": "assistant",
                            "content": "Here are the registered servers: ...",
                        },
                    ],
                },
            },
            "error_validation": {
                "success": False,
                "error": {
                    "code": -32602,
                    "message": "mcp_proxy_url is required",
                },
            },
            "error_internal": {
                "success": False,
                "error": {
                    "code": -32603,
                    "message": "Chat flow failed",
                    "data": {"original_error": "Connection refused"},
                },
            },
        },
    }
