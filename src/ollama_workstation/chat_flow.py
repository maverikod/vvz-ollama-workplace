"""
Core chat loop: OLLAMA /api/chat with tools, proxy execution, tool messages.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import httpx

from .config import WorkstationConfig
from .proxy_client import ProxyClient, ProxyClientError
from .tools import get_ollama_tools

if TYPE_CHECKING:
    from .tool_call_registry import ToolCallRegistry

logger = logging.getLogger(__name__)


def _tool_message(tool_name: str, content: str) -> Dict[str, Any]:
    """Build OLLAMA tool message: role tool, tool_name, content (spec 2.2)."""
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
            server_id = arguments.get("server_id")
            command = arguments.get("command")
            if not server_id or not str(server_id).strip():
                return json.dumps(
                    {
                        "error": "call_server requires server_id (from list_servers).",
                    }
                )
            if not command or not str(command).strip():
                return json.dumps(
                    {
                        "error": "call_server requires command name.",
                    }
                )
            out = await proxy.call_server(
                server_id=server_id,
                command=command,
                copy_number=arguments.get("copy_number"),
                params=arguments.get("params"),
            )
        elif tool_name == "help":
            server_id = arguments.get("server_id")
            if not server_id or not str(server_id).strip():
                return json.dumps(
                    {
                        "error": "help requires server_id (from list_servers). "
                        "Call list_servers first to get server_id values.",
                    }
                )
            out = await proxy.help(
                server_id=server_id,
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


async def _run_session_tool(
    proxy: ProxyClient,
    tool_registry: "ToolCallRegistry",
    tool_name: str,
    arguments: Dict[str, Any],
) -> str:
    """
    Execute one session-scoped tool: resolve display_name to (command, server_id),
    call proxy.call_server(server_id, command, params). Model never sees server_id.
    """
    try:
        command_name, server_id = tool_registry.resolve(tool_name)
        params = {k: v for k, v in arguments.items() if k not in ("copy_number",)}
        out = await proxy.call_server(
            server_id=server_id,
            command=command_name,
            copy_number=arguments.get("copy_number"),
            params=params,
        )
    except KeyError as e:
        logger.warning("Session tool %s not in registry: %s", tool_name, e)
        return json.dumps({"error": "Unknown tool: %s" % tool_name})
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
    session_tools: Optional[List[Dict[str, Any]]] = None,
    tool_registry: Optional["ToolCallRegistry"] = None,
    tools_from_file: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Run the OLLAMA chat loop with tools.

    When session_tools and tool_registry are set, the model sees only those
    tools (no list_servers/call_server/help); proxy and server_id are hidden.
    Otherwise uses tools_from_file (if provided) or default proxy tools.

    Args:
        config: Workstation config (proxy URL, OLLAMA URL, model, timeouts).
        messages: Initial messages.
        model: Override config model if set.
        stream: If True, request streaming (may defer in implementation).
        max_tool_rounds: Override config max_tool_rounds if set.
        session_tools: Optional OLLAMA-format tools (session allow-list only).
        tool_registry: When session_tools set, used to resolve tool name to
            (command_name, server_id) for proxy.call_server.

    Returns:
        Dict with "message", "history", and optionally "error" if failed.
    """
    use_model = model or config.ollama_model
    use_max_rounds = (
        max_tool_rounds if max_tool_rounds is not None else config.max_tool_rounds
    )
    tools = (
        session_tools
        if session_tools is not None and tool_registry is not None
        else (tools_from_file if tools_from_file else get_ollama_tools())
    )
    history: List[Dict[str, Any]] = list(messages)
    proxy = ProxyClient(config)
    use_registry = tool_registry is not None
    t_flow_start = time.perf_counter()

    logger.info(
        "chat_flow start model=%s max_rounds=%s session_tools=%s message_count=%s",
        use_model,
        use_max_rounds,
        use_registry,
        len(history),
    )

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

        # Log what the model sees (tool names + message summary).
        tool_names = []
        for t in tools:
            if isinstance(t, dict):
                fn = t.get("function") or {}
                tool_names.append(fn.get("name") or "?")
        msg_summary = []
        for m in history:
            role = m.get("role", "?")
            content = m.get("content") or ""
            tc = m.get("tool_calls") or []
            part = "role=%s content_len=%s" % (role, len(str(content)))
            if tc:
                part += " tool_calls=%s" % [
                    f.get("function", {}).get("name") for f in tc
                ]
            msg_summary.append(part)
        logger.info(
            "chat_flow model_sees round=%s tools=%s messages_summary=%s",
            round_num + 1,
            tool_names,
            msg_summary,
        )

        try:
            logger.debug(
                "chat_flow OLLAMA request round=%s url=%s/api/chat model=%s",
                round_num + 1,
                config.ollama_base_url,
                use_model,
            )
            t_ollama_start = time.perf_counter()
            async with httpx.AsyncClient(timeout=config.ollama_timeout) as client:
                resp = await client.post(
                    f"{config.ollama_base_url}/api/chat",
                    json=body,
                )
                resp.raise_for_status()
                data = resp.json()
            logger.info(
                "chat_flow OLLAMA round=%s duration_sec=%.3f",
                round_num + 1,
                time.perf_counter() - t_ollama_start,
            )
            # Log what the model returned.
            msg = data.get("message") or {}
            out_role = msg.get("role", "?")
            out_content = msg.get("content") or ""
            out_tc = msg.get("tool_calls") or []
            logger.info(
                "chat_flow model_reply round=%s role=%s content_len=%s tool_calls=%s",
                round_num + 1,
                out_role,
                len(str(out_content)),
                [f.get("function", {}).get("name") for f in out_tc] if out_tc else [],
            )
        except httpx.HTTPStatusError as e:
            logger.exception(
                "chat_flow OLLAMA HTTP error round=%s status=%s response=%s",
                round_num + 1,
                e.response.status_code if e.response else None,
                getattr(e.response, "text", "")[:500] if e.response else None,
            )
            err_msg = str(e)
            if e.response.status_code == 404:
                err_msg = (
                    "OLLAMA 404 at %s/api/chat. Check: (1) ollama_base_url "
                    "points to Ollama (Docker: host.docker.internal:11434 or "
                    "service name); (2) model '%s' exists (GET /api/tags); "
                    "(3) Ollama is running."
                ) % (config.ollama_base_url, use_model)
            return {
                "message": "",
                "history": history,
                "error": err_msg,
            }
        except Exception as e:  # noqa: BLE001
            logger.exception(
                "chat_flow OLLAMA request failed round=%s error=%s",
                round_num + 1,
                e,
            )
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
            logger.info(
                "chat_flow done duration_sec=%.3f rounds=%s",
                time.perf_counter() - t_flow_start,
                round_num + 1,
            )
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
            try:
                t_tool_start = time.perf_counter()
                if use_registry and tool_registry is not None:
                    logger.debug(
                        "chat_flow session_tool server_id from registry: %s", tname
                    )
                    content_str = await _run_session_tool(
                        proxy, tool_registry, tname, args_dict
                    )
                else:
                    content_str = await _run_tool(proxy, tname, args_dict)
                logger.info(
                    "chat_flow tool round=%s tool=%s duration_sec=%.3f",
                    round_num + 1,
                    tname,
                    time.perf_counter() - t_tool_start,
                )
            except Exception as e:  # noqa: BLE001
                logger.exception(
                    "chat_flow tool execution failed round=%s tool=%s error=%s",
                    round_num + 1,
                    tname,
                    e,
                )
                content_str = json.dumps({"error": str(e)})
            history.append(_tool_message(tname, content_str))

    await proxy.close()
    logger.info(
        "chat_flow done duration_sec=%.3f rounds=%s",
        time.perf_counter() - t_flow_start,
        use_max_rounds,
    )
    last_content = history[-1].get("content", "") if history else ""
    return {"message": last_content, "history": history}
