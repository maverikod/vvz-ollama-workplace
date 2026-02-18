"""
Adapter Command: ollama_chat — chat with OLLAMA using MCP Proxy tools.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult

from ..config import load_config
from ..chat_flow import run_chat_flow


class OllamaChatCommand(Command):
    """
    Run a chat with OLLAMA where the model can use MCP Proxy tools
    (list_servers, call_server, help). Accepts messages and optional model,
    stream, max_tool_rounds. Returns the final assistant message and
    optionally the full message history.
    """

    name = "ollama_chat"
    descr = (
        "Chat with OLLAMA using MCP Proxy tools. Send messages and optionally "
        "override model, stream, or max_tool_rounds. The model can list servers, "
        "call commands on any server registered in the proxy, and get help. "
        "Returns the final assistant reply and full history."
    )

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """JSON Schema for parameters; man-like descriptions and examples."""
        return {
            "type": "object",
            "description": (
                "Chat with OLLAMA; the model has access to MCP Proxy tools "
                "(list_servers, call_server, help)."
            ),
            "properties": {
                "messages": {
                    "type": "array",
                    "description": "Chat messages (role, content).",
                    "items": {
                        "type": "object",
                        "properties": {
                            "role": {"type": "string"},
                            "content": {"type": "string"},
                        },
                    },
                },
                "model": {
                    "type": "string",
                    "description": "OLLAMA model. Overrides config default.",
                },
                "stream": {
                    "type": "boolean",
                    "description": "Stream response. Default false.",
                    "default": False,
                },
                "max_tool_rounds": {
                    "type": "integer",
                    "description": "Max tool-call rounds. Overrides config if set.",
                },
                "config_path": {
                    "type": "string",
                    "description": "Optional path to config file (YAML/JSON).",
                },
            },
            "required": ["messages"],
            "additionalProperties": True,
            "examples": [
                {
                    "command": "ollama_chat",
                    "params": {
                        "messages": [{"role": "user", "content": "List servers."}],
                    },
                    "description": "One user message; model may call list_servers.",
                },
                {
                    "command": "ollama_chat",
                    "params": {
                        "messages": [{"role": "user", "content": "What can you do?"}],
                        "model": "llama3.1",
                    },
                    "description": "Override model; reply may use tools.",
                },
            ],
        }

    async def execute(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        stream: bool = False,
        max_tool_rounds: Optional[int] = None,
        config_path: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """
        Load config, run chat flow with OLLAMA and proxy tools, return result.
        """
        try:
            config = load_config(config_path)
        except ValueError as e:
            return ErrorResult(message=str(e), code=-32602)
        except Exception as e:  # noqa: BLE001
            return ErrorResult(message=f"Config load failed: {e}", code=-32603)

        result = await run_chat_flow(
            config=config,
            messages=messages,
            model=model,
            stream=stream,
            max_tool_rounds=max_tool_rounds,
        )
        if result.get("error"):
            return ErrorResult(
                message=result["error"],
                code=-32603,
            )
        return SuccessResult(
            data={
                "message": result.get("message", ""),
                "history": result.get("history", []),
            },
        )
