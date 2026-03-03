"""
Adapter command: list — Ollama GET /api/tags (ollama-server surface).

Returns list of available models.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

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


class OllamaServerListCommand(Command):
    """
    Call Ollama GET /api/tags to list available models.
    Returns models array (name, size, digest, etc.).
    """

    name = "list"
    descr = "Ollama list: GET /api/tags. Returns list of available models."

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """No parameters; strict schema."""
        return {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        }

    @classmethod
    def get_result_schema(cls) -> Dict[str, Any]:
        """Result: models array."""
        return {
            "type": "object",
            "properties": {
                "models": {
                    "type": "array",
                    "description": "List of model info objects from /api/tags",
                    "items": {"type": "object"},
                },
            },
            "required": ["models"],
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

    async def execute(self, **kwargs: Any) -> Any:
        """GET Ollama /api/tags; return models list."""
        config_data = _get_config_data()
        base_url, timeout = get_ollama_server_settings(config_data)

        try:
            raw = await asyncio.to_thread(
                _sync_get_tags,
                base_url,
                timeout,
            )
        except httpx.HTTPStatusError as e:
            msg = (e.response.text or str(e))[:500] if e.response else str(e)
            logger.warning("ollama-server list HTTP error: %s", msg)
            return ErrorResult(message="Ollama list failed: %s" % msg, code=-32603)
        except Exception as e:
            logger.warning("ollama-server list failed: %s", e)
            return ErrorResult(message="Ollama list failed: %s" % e, code=-32603)

        models = raw.get("models") if isinstance(raw, dict) else []
        if not isinstance(models, list):
            models = []
        return SuccessResult(data={"models": models})


def _sync_get_tags(base_url: str, timeout: float) -> Dict[str, Any]:
    """Sync GET /api/tags."""
    url = "%s/api/tags" % base_url.rstrip("/")
    with httpx.Client(timeout=timeout) as client:
        resp = client.get(url)
        resp.raise_for_status()
        result: Dict[str, Any] = resp.json()
        return result
