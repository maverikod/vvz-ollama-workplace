"""
Adapter command: direct_chat — call OLLAMA /api/chat only, no session/tools/context.

Use to check if slowness is in the model or in adapter code (session, context, tools).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult

from ..config import load_config
from ..model_loading_state import get_active_model
from ..model_provider_resolver import resolve_model_endpoint
from ..commercial_chat_client import chat_completion as commercial_chat_completion
from ..provider_registry import get_default_client

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_PATH = os.environ.get(
    "ADAPTER_CONFIG_PATH", "/app/config/adapter_config.json"
)


class DirectChatCommand(Command):
    """
    Call OLLAMA /api/chat with one user message. No session, Redis, tools, context.
    Returns assistant reply and duration_sec to see if the bottleneck is the model.
    """

    name = "direct_chat"
    descr = (
        "Direct call to OLLAMA /api/chat with a single user message. "
        "No session, no tools, no context building. Returns reply and duration_sec."
    )

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Parameters: content (required), optional model, config_path."""
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "User message to send to the model",
                },
                "model": {
                    "type": "string",
                    "description": "Model name; omit to use active_model or config",
                },
                "config_path": {
                    "type": "string",
                    "description": "Config path; omit for default",
                },
            },
            "required": ["content"],
        }

    @classmethod
    def get_result_schema(cls) -> Dict[str, Any]:
        """Result: message, duration_sec, model."""
        return {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Assistant reply"},
                "duration_sec": {
                    "type": "number",
                    "description": "Time from request to response",
                },
                "model": {"type": "string", "description": "Model used"},
            },
            "required": ["message", "duration_sec", "model"],
        }

    @classmethod
    def get_error_schema(cls) -> Dict[str, Any]:
        """Error: message, optional code."""
        return {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "code": {"type": "integer"},
            },
        }

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Metadata for the command."""
        return {
            "name": cls.name,
            "description": (cls.__doc__ or cls.descr or "").strip(),
            "params": cls.get_schema(),
            "result_schema": cls.get_result_schema(),
            "error_schema": cls.get_error_schema(),
            "error_codes": [],
            "examples": {
                "ok": {
                    "success": True,
                    "data": {
                        "message": "Hello!",
                        "duration_sec": 1.23,
                        "model": "llama3.2",
                    },
                },
            },
        }

    async def execute(self, **kwargs: Any) -> Any:
        """POST to OLLAMA /api/chat only; return reply and duration."""
        content = (kwargs.get("content") or "").strip()
        if not content:
            return ErrorResult(message="content is required", code=-32602)
        config_path: Optional[str] = kwargs.get("config_path")
        path = config_path or (
            _DEFAULT_CONFIG_PATH if Path(_DEFAULT_CONFIG_PATH).exists() else None
        )
        if path is None:
            return ErrorResult(
                message="Config not found; set config_path or ADAPTER_CONFIG_PATH",
                code=-32603,
            )
        config = load_config(path)
        model = (
            (kwargs.get("model") or "").strip()
            or get_active_model()
            or ((config.ollama_model or "").strip())
        )
        if not model:
            return ErrorResult(
                message="model not set (param, active_model, or config)",
                code=-32603,
            )
        endpoint = resolve_model_endpoint(model, config)
        timeout = max(30.0, float(config.ollama_timeout or 60))
        t0 = time.perf_counter()
        try:
            if endpoint.is_ollama:
                if not getattr(config, "provider_clients_data", None):
                    return ErrorResult(
                        message="provider_clients_data missing; cannot use Ollama.",
                        code=-32603,
                    )
                provider_client = get_default_client(config.provider_clients_data)
                body = {
                    "model": model,
                    "messages": [{"role": "user", "content": content}],
                    "stream": False,
                }
                data = await asyncio.to_thread(provider_client.chat, body)
                duration = time.perf_counter() - t0
            else:
                data = await commercial_chat_completion(
                    endpoint,
                    [{"role": "user", "content": content}],
                    stream=False,
                    timeout=timeout,
                )
                duration = time.perf_counter() - t0
            msg_obj = data.get("message")
            if isinstance(msg_obj, dict):
                reply = (msg_obj.get("content") or "").strip()
            else:
                reply = str(data.get("message", ""))
        except Exception as e:
            duration = time.perf_counter() - t0
            logger.exception("direct_chat failed after %.2fs: %s", duration, e)
            return ErrorResult(
                message="Chat request failed: %s" % e,
                code=-32603,
            )
        return SuccessResult(
            data={
                "message": reply or "(empty)",
                "duration_sec": round(duration, 2),
                "model": model,
            }
        )
