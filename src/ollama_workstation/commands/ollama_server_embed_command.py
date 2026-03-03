"""
Adapter command: embed — Ollama POST /api/embed (ollama-server surface).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Union

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


class OllamaServerEmbedCommand(Command):
    """
    Call Ollama POST /api/embed with model and input (string or list of strings).
    Returns embeddings array and optional model, prompt_eval_count.
    """

    name = "embed"
    descr = (
        "Ollama embed: POST /api/embed with model and input "
        "(string or list of strings). Returns embeddings array."
    )

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Strict JSON Schema for parameters."""
        return {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "Embedding model name",
                },
                "input": {
                    "description": "Text or list of texts to embed.",
                    "oneOf": [
                        {"type": "string"},
                        {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    ],
                },
            },
            "required": ["model", "input"],
            "additionalProperties": False,
        }

    @classmethod
    def get_result_schema(cls) -> Dict[str, Any]:
        """Result: embeddings, model, prompt_eval_count."""
        return {
            "type": "object",
            "properties": {
                "embeddings": {
                    "type": "array",
                    "description": "Embedding vectors",
                },
                "model": {"type": ["string", "null"]},
                "prompt_eval_count": {"type": ["integer", "null"]},
            },
            "required": ["embeddings"],
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
        model: str = "",
        input_: Union[str, List[str], None] = None,
        **kwargs: Any,
    ) -> Any:
        """POST to Ollama /api/embed; return embeddings."""
        config_data = _get_config_data()
        base_url, timeout = get_ollama_server_settings(config_data)

        inp = kwargs.get("input", input_)
        if not (model or "").strip():
            return ErrorResult(message="model is required", code=-32602)
        if inp is None:
            return ErrorResult(
                message="input is required (string or array of strings)", code=-32602
            )
        if not isinstance(inp, (str, list)):
            return ErrorResult(
                message="input must be string or array of strings", code=-32602
            )
        if isinstance(inp, list) and not all(isinstance(x, str) for x in inp):
            return ErrorResult(
                message="input array must contain only strings", code=-32602
            )

        body: Dict[str, Any] = {"model": model.strip(), "input": inp}

        try:
            raw = await asyncio.to_thread(
                _sync_post_embed,
                base_url,
                body,
                timeout,
            )
        except httpx.HTTPStatusError as e:
            msg = (e.response.text or str(e))[:500] if e.response else str(e)
            logger.warning("ollama-server embed HTTP error: %s", msg)
            return ErrorResult(message="Ollama embed failed: %s" % msg, code=-32603)
        except Exception as e:
            logger.warning("ollama-server embed failed: %s", e)
            return ErrorResult(message="Ollama embed failed: %s" % e, code=-32603)

        return SuccessResult(
            data={
                "embeddings": raw.get("embeddings", []),
                "model": raw.get("model"),
                "prompt_eval_count": raw.get("prompt_eval_count"),
            }
        )


def _sync_post_embed(
    base_url: str, body: Dict[str, Any], timeout: float
) -> Dict[str, Any]:
    """Sync POST /api/embed."""
    url = "%s/api/embed" % base_url.rstrip("/")
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(url, json=body)
        resp.raise_for_status()
        result: Dict[str, Any] = resp.json()
        return result
