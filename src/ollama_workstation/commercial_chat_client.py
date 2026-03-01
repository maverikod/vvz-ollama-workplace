"""
Chat client for commercial providers (OpenAI-compatible and OpenRouter).

Sends POST to /v1/chat/completions with OpenAI format. Converts to/from
Ollama-style message format for compatibility with chat_flow.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from .model_provider_resolver import ModelEndpoint

logger = logging.getLogger(__name__)


def _ollama_to_openai_messages(
    ollama_messages: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Convert Ollama message format to OpenAI format.

    Ollama: role, content, tool_calls (optional), tool_name (for tool role).
    OpenAI: role, content, tool_calls (optional).
    """
    out: List[Dict[str, Any]] = []
    for m in ollama_messages or []:
        role = (m.get("role") or "user").strip().lower()
        content = m.get("content") or ""
        if role == "tool":
            out.append({"role": "user", "content": content})
            continue
        elif role not in ("system", "user", "assistant"):
            role = "user"
        entry: Dict[str, Any] = {"role": role, "content": content}
        if m.get("tool_calls"):
            entry["tool_calls"] = m["tool_calls"]
        out.append(entry)
    return out


def _openai_to_ollama_message(openai_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract assistant message from OpenAI response to Ollama format.

    OpenAI: choices[0].message with role, content, tool_calls.
    Ollama: {role, content, tool_calls}.
    """
    choices = openai_response.get("choices") or []
    if not choices:
        return {"role": "assistant", "content": ""}
    msg = choices[0].get("message") or {}
    return {
        "role": msg.get("role") or "assistant",
        "content": msg.get("content") or "",
        "tool_calls": msg.get("tool_calls") or [],
    }


async def chat_completion(
    endpoint: ModelEndpoint,
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None,
    stream: bool = False,
    timeout: float = 120.0,
) -> Dict[str, Any]:
    """
    Send chat completion to OpenAI-compatible endpoint.

    Args:
        endpoint: Resolved ModelEndpoint (base_url, api_key, model_id).
        messages: Ollama-style messages (role, content, tool_calls).
        tools: Optional tool definitions (OpenAI format).
        stream: Whether to stream (not implemented for now).
        timeout: Request timeout in seconds.

    Returns:
        Ollama-style response: {message: {role, content, tool_calls}, ...}.
    """
    base = endpoint.base_url.rstrip("/")
    chat_url = f"{base}/chat/completions"

    body: Dict[str, Any] = {
        "model": endpoint.model_id,
        "messages": _ollama_to_openai_messages(messages),
        "stream": False,
    }
    if tools:
        body["tools"] = tools

    headers: Dict[str, str] = {"Content-Type": "application/json"}
    if endpoint.api_key:
        headers["Authorization"] = "Bearer %s" % endpoint.api_key.strip()

    if stream:
        body["stream"] = True

    logger.debug(
        "commercial_chat POST %s model=%s messages=%s",
        chat_url,
        endpoint.model_id,
        len(messages),
    )
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(chat_url, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.warning(
            "commercial_chat HTTP %s %s: %s",
            e.response.status_code if e.response else None,
            endpoint.model_id,
            (e.response.text or "")[:500] if e.response else None,
        )
        raise
    except Exception as e:
        logger.warning("commercial_chat failed %s: %s", endpoint.model_id, e)
        raise

    msg = _openai_to_ollama_message(data)
    return {
        "message": msg,
        "prompt_eval_count": data.get("usage", {}).get("prompt_tokens"),
        "eval_count": data.get("usage", {}).get("completion_tokens"),
    }
