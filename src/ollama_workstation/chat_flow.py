"""
Core chat loop: OLLAMA /api/chat with tools, proxy execution, and tool message appends.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from .config import WorkstationConfig
from .proxy_client import ProxyClient, ProxyClientError
from .tools import get_ollama_tools

logger = logging.getLogger(__name__)


def _tool_message(tool_name: str, content: str) -> Dict[str, Any]:
    """Build OLLAMA tool message: role tool, tool_name, content (per tech spec 2.2)."""
    return {
        "role": "tool",
        "tool_name": tool_name,
        "content": content,
    }


async def _run_tool(
    proxy: ProxyClient,
    tool_name: str,
    arguments: Dict[str, Any],
) -> str:
    """
    Execute one tool call via proxy; return content string for tool message.
    On error return error string so model sees it (do not drop conversation).
    """
    try:
        if tool_name == "list_servers":
            out = await proxy.list_servers(
                page=arguments.get("page"),
                page_size=arguments.get("page_size"),
                filter_enabled=arguments.get("filter_enabled"),
            )
        elif tool_name == "call_server":
            out = await proxy.call_server(
                server_id=arguments["server_id"],
                command=arguments["command"],
                copy_number=arguments.get("copy_number"),
                params=arguments.get("params"),
            )
        elif tool_name == "help":
            out = await proxy.help(
                server_id=arguments["server_id"],
                copy_number=arguments.get("copy_number"),
                command=arguments.get("command"),
            )
        else:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})
    except ProxyClientError as e:
        logger.warning(
            "Tool %s proxy error (status=%s): %s", tool_name, e.status, e.message
        )
        return json.dumps({"error": e.message, "status": e.status})
    except Exception as e:  # noqa: BLE001
        logger.exception("Tool %s failed: %s", tool_name, e)
        return json.dumps({"error": str(e)})

    if isinstance(out, dict):
        return json.dumps(out)
    return str(out)


async def run_chat_flow(
    config: WorkstationConfig,
    messages: List[Dict[str, Any]],
    model: Optional[str] = None,
    stream: bool = False,
    max_tool_rounds: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Run the OLLAMA chat loop with MCP Proxy tools.

    1. Build request to OLLAMA /api/chat with model, messages, tools.
    2. On tool_calls, call proxy for each, append tool messages.
    3. Repeat until no tool_calls or max_tool_rounds reached.
    4. Return final assistant message and full history.

    Args:
        config: Workstation config (proxy URL, OLLAMA URL, model, timeouts).
        messages: Initial message list (e.g. [{"role": "user", "content": "..."}]).
        model: Override config model if set.
        stream: If True, request streaming (implementation may defer streaming).
        max_tool_rounds: Override config max_tool_rounds if set.

    Returns:
        Dict with "message" (final assistant message content or last message),
        "history" (full messages list), and optionally "error" if failed.
    """
    use_model = model or config.ollama_model
    use_max_rounds = (
        max_tool_rounds
        if max_tool_rounds is not None
        else config.max_tool_rounds
    )
    tools = get_ollama_tools()
    history: List[Dict[str, Any]] = list(messages)
    proxy = ProxyClient(config)

    try:
        import httpx
    except ImportError:
        return {
            "message": "",
            "history": history,
            "error": "httpx not installed; required for OLLAMA requests",
        }

    for round_num in range(use_max_rounds):
        body: Dict[str, Any] = {
            "model": use_model,
            "messages": history,
            "tools": tools,
        }
        if stream:
            body["stream"] = True
        # Non-streaming: we need full response with possible tool_calls
        body["stream"] = False

        try:
            async with httpx.AsyncClient(timeout=config.ollama_timeout) as client:
                resp = await client.post(
                    f"{config.ollama_base_url}/api/chat",
                    json=body,
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:  # noqa: BLE001
            logger.exception("OLLAMA request failed: %s", e)
            return {
                "message": "",
                "history": history,
                "error": str(e),
            }

        msg = data.get("message") or {}
        role = msg.get("role", "assistant")
        content = msg.get("content") or ""
        tool_calls = msg.get("tool_calls") or []

        entry = {"role": role, "content": content}
        if tool_calls:
            entry["tool_calls"] = tool_calls
        history.append(entry)

        if not tool_calls:
            await proxy.close()
            return {"message": content, "history": history}

        # Log tool invocations (name, args keys, no secrets)
        for tc in tool_calls:
            fn = tc.get("function") or {}
            tname = fn.get("name") or "?"
            args_raw = fn.get("arguments")
            if isinstance(args_raw, str):
                try:
                    args_dict = json.loads(args_raw)
                except json.JSONDecodeError:
                    args_dict = {}
            else:
                args_dict = args_raw or {}
            logger.info(
                "Tool invocation round=%s tool=%s args_keys=%s",
                round_num + 1,
                tname,
                list(args_dict.keys()),
            )

        for tc in tool_calls:
            fn = tc.get("function") or {}
            tname = fn.get("name") or "unknown"
            args_raw = fn.get("arguments")
            if isinstance(args_raw, str):
                try:
                    args_dict = json.loads(args_raw)
                except json.JSONDecodeError:
                    args_dict = {}
            else:
                args_dict = args_raw or {}
            content_str = await _run_tool(proxy, tname, args_dict)
            history.append(_tool_message(tname, content_str))

    await proxy.close()
    last_content = history[-1].get("content", "") if history else ""
    return {"message": last_content, "history": history}
