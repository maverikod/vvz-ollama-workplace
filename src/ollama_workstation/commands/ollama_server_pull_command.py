"""
Adapter command: pull — Ollama POST /api/pull (ollama-server surface).

Pull a model by name; optional stream and insecure.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

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


class OllamaServerPullCommand(Command):
    """
    Call Ollama POST /api/pull to download a model by name.
    Optional stream (default false), insecure (allow insecure registry).
    Returns status (success or error message).
    """

    name = "pull"
    descr = (
        "Ollama pull: POST /api/pull to download a model. "
        "Required: name. Optional: stream, insecure."
    )

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Strict JSON Schema for parameters."""
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Model name or name:tag to pull (e.g. llama3.2)",
                },
                "stream": {
                    "type": "boolean",
                    "description": "Stream progress; default false",
                    "default": False,
                },
                "insecure": {
                    "type": "boolean",
                    "description": "Allow insecure registry",
                    "default": False,
                },
            },
            "required": ["name"],
            "additionalProperties": False,
        }

    @classmethod
    def get_result_schema(cls) -> Dict[str, Any]:
        """Result: status, optional message."""
        return {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "success or error",
                },
                "message": {
                    "type": "string",
                    "description": "Optional message (e.g. error detail)",
                },
            },
            "required": ["status"],
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
        name: Optional[str] = None,
        stream: bool = False,
        insecure: bool = False,
        **kwargs: Any,
    ) -> Any:
        """POST to Ollama /api/pull; return status."""
        config_data = _get_config_data()
        base_url, timeout = get_ollama_server_settings(config_data)

        model_name = (name or kwargs.get("name") or "").strip()
        if not model_name:
            return ErrorResult(
                message="name is required (model name or name:tag)", code=-32602
            )

        body: Dict[str, Any] = {
            "name": model_name,
            "stream": bool(stream),
            "insecure": bool(insecure),
        }

        try:
            ok = await asyncio.to_thread(
                _sync_post_pull,
                base_url,
                body,
                timeout,
            )
        except httpx.HTTPStatusError as e:
            msg = (e.response.text or str(e))[:500] if e.response else str(e)
            logger.warning("ollama-server pull HTTP error: %s", msg)
            return ErrorResult(message="Ollama pull failed: %s" % msg, code=-32603)
        except Exception as e:
            logger.warning("ollama-server pull failed: %s", e)
            return ErrorResult(message="Ollama pull failed: %s" % e, code=-32603)

        return SuccessResult(
            data={
                "status": "success" if ok else "error",
                "message": None if ok else "Pull failed",
            }
        )


def _sync_post_pull(base_url: str, body: Dict[str, Any], timeout: float) -> bool:
    """Sync POST /api/pull. Returns True on 200."""
    url = "%s/api/pull" % base_url.rstrip("/")
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(url, json=body)
        return resp.status_code == 200
