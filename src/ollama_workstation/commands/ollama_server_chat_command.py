"""
Adapter command: chat — Ollama POST /api/chat (ollama-server surface).

Single request/response; no tool loop. Used when adapter registers as ollama-server.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx
from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult

from ..ollama_server_config import get_ollama_server_settings

logger = logging.getLogger(__name__)


def _get_config_data() -> Any:
    """Adapter config dict from mcp_proxy_adapter."""
    try:
        from mcp_proxy_adapter.config import get_config

        return getattr(get_config(), "config_data", None)
    except Exception:
        return None


class OllamaServerChatCommand(Command):
    """
    Call Ollama POST /api/chat with model and messages. No tool loop.
    Returns message, prompt_eval_count, eval_count.
    """

    name = "chat"
    descr = (
        "Ollama chat: POST /api/chat with model and messages. "
        "Optional tools and stream. Returns assistant message and token counts."
    )

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Strict JSON Schema for parameters."""
        return {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "Model name (e.g. llama3.2)",
                },
                "messages": {
                    "type": "array",
                    "description": "Chat messages: [{role, content}, ...]",
                    "items": {
                        "type": "object",
                        "properties": {
                            "role": {"type": "string"},
                            "content": {"type": "string"},
                        },
                        "required": ["role", "content"],
                        "additionalProperties": False,
                    },
                },
                "tools": {
                    "type": "array",
                    "description": "Optional tool definitions for the model",
                },
                "stream": {
                    "type": "boolean",
                    "description": "Stream response; default false",
                    "default": False,
                },
            },
            "required": ["model", "messages"],
            "additionalProperties": False,
        }

    @classmethod
    def get_result_schema(cls) -> Dict[str, Any]:
        """Result: message, prompt_eval_count, eval_count."""
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "object",
                    "description": (
                        "Assistant message (role, content, optional tool_calls)"
                    ),
                },
                "prompt_eval_count": {"type": ["integer", "null"]},
                "eval_count": {"type": ["integer", "null"]},
            },
            "required": ["message"],
            "additionalProperties": False,
        }

    @classmethod
    def get_error_schema(cls) -> Dict[str, Any]:
        """Error: message, code."""
        return {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "code": {"type": "integer"},
            },
            "additionalProperties": False,
        }

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Metadata for discovery/help."""
        return {
            "name": cls.name,
            "description": (cls.__doc__ or cls.descr or "").strip(),
            "params": cls.get_schema(),
            "result_schema": cls.get_result_schema(),
            "error_schema": cls.get_error_schema(),
            "error_codes": [],
            "examples": {},
        }

    async def execute(
        self,
        model: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Any]] = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> Any:
        """POST to Ollama /api/chat; return normalized response."""
        config_data = _get_config_data()
        base_url, timeout = get_ollama_server_settings(config_data)

        model_str = (model or "").strip() if model is not None else ""
        if not model_str:
            return ErrorResult(message="model is required", code=-32602)
        if not isinstance(messages, list) or len(messages) == 0:
            return ErrorResult(
                message="messages must be a non-empty array", code=-32602
            )

        body: Dict[str, Any] = {
            "model": model_str,
            "messages": messages,
            "stream": bool(stream),
        }
        if tools:
            body["tools"] = tools

        try:
            raw = await asyncio.to_thread(
                _sync_post_chat,
                base_url,
                body,
                timeout,
            )
        except httpx.HTTPStatusError as e:
            msg = (e.response.text or str(e))[:500] if e.response else str(e)
            logger.warning("ollama-server chat HTTP error: %s", msg)
            return ErrorResult(message="Ollama chat failed: %s" % msg, code=-32603)
        except Exception as e:
            logger.warning("ollama-server chat failed: %s", e)
            return ErrorResult(message="Ollama chat failed: %s" % e, code=-32603)

        return SuccessResult(
            data={
                "message": raw.get("message", {}),
                "prompt_eval_count": raw.get("prompt_eval_count"),
                "eval_count": raw.get("eval_count"),
            }
        )


def _sync_post_chat(
    base_url: str, body: Dict[str, Any], timeout: float
) -> Dict[str, Any]:
    """Sync POST /api/chat."""
    url = "%s/api/chat" % base_url.rstrip("/")
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(url, json=body)
        resp.raise_for_status()
        result: Dict[str, Any] = resp.json()
        return result
