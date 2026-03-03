"""
Core chat loop: OLLAMA /api/chat with tools, proxy execution, tool messages.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import httpx

from .command_alias_registry import CommandAliasRegistry
from .command_discovery import CommandDiscovery
from .config import WorkstationConfig
from .tools import HELP_REFERENCE_TEXT
from .effective_tool_list_builder import EffectiveToolListBuilder
from .ollama_representation import OllamaRepresentation, register_ollama_models
from .model_loading_state import get_active_model, is_model_ready
from .model_provider_resolver import resolve_model_endpoint
from .commercial_chat_client import chat_completion as commercial_chat_completion
from .proxy_client import ProxyClient, ProxyClientError
from .provider_registry import get_default_client
from .representation_registry import RepresentationRegistry
from .safe_name_translator import SafeNameTranslator
from .context_representation import ContextRepresentation
from .session_entity import Session

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
    representation: Optional[ContextRepresentation] = None,
) -> str:
    """
    Execute one tool via proxy only (list_servers, call_server, help).
    If representation is set, result is translated via format_tool_result.
    """
    try:
        if tool_name == "list_servers":
            out = await proxy.list_servers(
                page=arguments.get("page"),
                page_size=arguments.get("page_size"),
                filter_enabled=arguments.get("filter_enabled"),
            )
        elif tool_name == "call_server":
            server_id = (arguments.get("server_id") or "").strip()
            command = (arguments.get("command") or "").strip()
            if not server_id:
                return json.dumps(
                    {"error": "call_server requires server_id (from list_servers)."}
                )
            if not command:
                return json.dumps({"error": "call_server requires command name."})
            out = await proxy.call_server(
                server_id,
                command,
                params=arguments.get("params"),
            )
        elif tool_name == "help":
            server_id = (arguments.get("server_id") or "").strip()
            if not server_id:
                return json.dumps(
                    {
                        "error": "help requires server_id (from list_servers). "
                        "Call list_servers first to get server_id values.",
                    }
                )
            out = await proxy.help(
                server_id,
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

    if representation is not None:
        return representation.format_tool_result(out)
    if isinstance(out, dict):
        return json.dumps(out)
    return str(out)


async def run_tool(
    config: WorkstationConfig,
    tool_name: str,
    arguments: Dict[str, Any],
) -> str:
    """
    Execute one tool via proxy only (list_servers, call_server, help).
    Returns content string as the model would see.
    """
    proxy = ProxyClient(config)
    try:
        return await _run_tool(proxy, tool_name, arguments)
    finally:
        await proxy.close()


async def run_tool_like_model(
    config: WorkstationConfig,
    tool_name: str,
    arguments: Dict[str, Any],
) -> str:
    """
    Invoke a tool the same way the model does (canonical then representation).
    Builds discovery + registry, resolves, calls proxy; raw result is
    translated via representation.format_tool_result to standard form.
    """
    proxy = ProxyClient(config)
    registry = RepresentationRegistry(default=OllamaRepresentation())
    register_ollama_models(registry, getattr(config, "ollama_models", None) or [])
    representation = registry.get_representation(
        get_active_model() or config.ollama_model or ""
    )
    try:
        discovery = CommandDiscovery(
            proxy,
            discovery_interval_sec=getattr(config, "command_discovery_interval_sec", 0),
        )
        await discovery.refresh()
        discovered = discovery.get_discovered_commands(available_only=False)
        builder = EffectiveToolListBuilder(
            CommandAliasRegistry(),
            SafeNameTranslator(),
        )
        minimal_session = Session.create()
        _tool_list, tool_registry = builder.build(
            minimal_session,
            config.commands_policy_config,
            discovered,
            preferred_server_id=getattr(config, "adapter_server_id", None) or None,
        )
        try:
            tool_registry.resolve(tool_name)
        except KeyError:
            if tool_name == "help" and (
                arguments.get("command_name") or arguments.get("cmdname")
            ):
                return await _run_help_for_model(
                    proxy,
                    tool_registry,
                    arguments,
                    representation,
                )
            if tool_name in ("list_servers", "call_server", "help"):
                return await _run_tool(
                    proxy,
                    tool_name,
                    arguments,
                    representation=representation,
                )
            return representation.format_tool_result(
                {"error": "Unknown tool: %s" % tool_name}
            )
        return await _run_session_tool(
            proxy,
            tool_registry,
            tool_name,
            arguments,
            representation,
        )
    finally:
        await proxy.close()


async def _run_help_for_model(
    proxy: ProxyClient,
    tool_registry: "ToolCallRegistry",
    arguments: Dict[str, Any],
    representation: ContextRepresentation,
) -> str:
    """
    Run help by command name: resolve command_name to server_id, get full
    description via proxy.help(server_id, command=cmd).
    """
    command_name = (
        (arguments.get("command_name") or arguments.get("cmdname")) or ""
    ).strip()
    if not command_name:
        return representation.format_tool_result({"help": HELP_REFERENCE_TEXT})
    try:
        cmd, server_id = tool_registry.resolve(command_name)
    except KeyError:
        return representation.format_tool_result(
            {"error": "Unknown command: %s" % command_name}
        )
    try:
        out = await proxy.help(server_id, command=cmd)
        return representation.format_tool_result(out)
    except Exception as e:  # noqa: BLE001
        logger.warning("help(%s) failed: %s", command_name, e)
        return representation.format_tool_result({"error": str(e)})


async def _run_session_tool(
    proxy: ProxyClient,
    tool_registry: "ToolCallRegistry",
    tool_name: str,
    arguments: Dict[str, Any],
    representation: ContextRepresentation,
) -> str:
    """
    Execute one session-scoped tool: resolve to server_id and command,
    call proxy.call_server(server_id, command, params); translate result
    via representation.format_tool_result.
    """
    try:
        command_name, server_id = tool_registry.resolve(tool_name)
        params = {k: v for k, v in arguments.items() if k not in ("copy_number",)}
        raw_out = await proxy.call_server(
            server_id,
            command_name,
            params=params,
        )
        return representation.format_tool_result(raw_out)
    except KeyError as e:
        logger.warning("Session tool %s not in registry: %s", tool_name, e)
        return representation.format_tool_result(
            {"error": "Unknown tool: %s" % tool_name}
        )
    except ProxyClientError as e:
        logger.warning(
            "Tool %s proxy error (status=%s): %s", tool_name, e.status, e.message
        )
        return representation.format_tool_result(
            {"error": e.message, "status": e.status}
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("Tool %s failed: %s", tool_name, e)
        return representation.format_tool_result({"error": str(e)})


async def run_chat_flow(
    config: WorkstationConfig,
    messages: List[Dict[str, Any]],
    model: Optional[str] = None,
    stream: bool = False,
    max_tool_rounds: Optional[int] = None,
    session_tools: Optional[List[Dict[str, Any]]] = None,
    tool_registry: Optional["ToolCallRegistry"] = None,
    tools_from_file: Optional[List[Dict[str, Any]]] = None,
    representation: Optional[ContextRepresentation] = None,
) -> Dict[str, Any]:
    """
    Run the chat loop with tools. Canonical layer (resolve, direct call) runs
    first; representation layer translates tool results to standard form.

    Args:
        representation: Used to format_tool_result(raw) for tool message content.
            If None, a default is used (OllamaRepresentation).
    """
    use_model = model or get_active_model() or config.ollama_model
    endpoint = resolve_model_endpoint(use_model, config)
    if representation is None:
        from .ollama_representation import OllamaRepresentation

        representation = OllamaRepresentation()
    use_max_rounds = (
        max_tool_rounds if max_tool_rounds is not None else config.max_tool_rounds
    )
    # Model sees only server-originated tools (from discovery). list_servers /
    # call_server / help are used internally and never sent to the model.
    tools = (
        session_tools
        if session_tools is not None and tool_registry is not None
        else (tools_from_file if tools_from_file else [])
    )
    if endpoint.is_ollama and not is_model_ready():
        return {
            "message": "",
            "history": list(messages),
            "error": "Model not ready; waiting for OLLAMA to respond.",
        }

    history: List[Dict[str, Any]] = list(messages)
    proxy = ProxyClient(config)
    use_registry = tool_registry is not None
    t_flow_start = time.perf_counter()
    total_prompt_tokens = 0
    total_eval_tokens = 0
    provider_client = None
    if endpoint.is_ollama and config.provider_clients_data:
        provider_client = get_default_client(config.provider_clients_data)

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

        # Log context size for token usage evaluation (chars and rough token estimate).
        ctx_msg_count = len(history)
        ctx_content_chars = sum(len(str(m.get("content") or "")) for m in history)
        ctx_tokens_estimate = ctx_content_chars // 4
        logger.info(
            "chat_flow context_size round=%s messages=%s chars=%s tokens_est=%s",
            round_num + 1,
            ctx_msg_count,
            ctx_content_chars,
            ctx_tokens_estimate,
        )

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
        # Log context content so it is visible what the model receives.
        _CONTEXT_PREVIEW_CHARS = 500
        for i, m in enumerate(history):
            role = m.get("role", "?")
            content = (m.get("content") or "").strip().replace("\n", " ")
            preview = content[:_CONTEXT_PREVIEW_CHARS] + (
                "..." if len(content) > _CONTEXT_PREVIEW_CHARS else ""
            )
            if preview:
                logger.info(
                    "chat_flow model_context message[%s] role=%s content_preview=%s",
                    i,
                    role,
                    preview,
                )

        try:
            t_ollama_start = time.perf_counter()
            if endpoint.is_ollama:
                logger.debug(
                    "chat_flow OLLAMA request round=%s model=%s (provider client)",
                    round_num + 1,
                    use_model,
                )
                if provider_client is None:
                    raise ValueError(
                        "Ollama provider client not available; "
                        "provider_clients_data missing or invalid."
                    )
                data = await asyncio.to_thread(provider_client.chat, body)
            else:
                # Same full context (standards, rules, last_n, relevance slot, tools)
                # as for Ollama; history is built once in ollama_chat and passed here.
                logger.debug(
                    "chat_flow commercial request round=%s provider=%s model=%s",
                    round_num + 1,
                    endpoint.provider,
                    endpoint.model_id,
                )
                data = await commercial_chat_completion(
                    endpoint,
                    history,
                    tools=tools if tools else None,
                    stream=False,
                    timeout=config.ollama_timeout,
                )
            # Log token usage from OLLAMA response (for cost/effect evaluation).
            prompt_tokens = data.get("prompt_eval_count")
            eval_tokens = data.get("eval_count")
            if prompt_tokens is not None:
                total_prompt_tokens += int(prompt_tokens)
            if eval_tokens is not None:
                total_eval_tokens += int(eval_tokens)
            logger.info(
                "chat_flow token_usage round=%s prompt_eval=%s eval=%s "
                "total_prompt=%s total_eval=%s",
                round_num + 1,
                prompt_tokens,
                eval_tokens,
                total_prompt_tokens,
                total_eval_tokens,
            )
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
                "chat_flow HTTP error round=%s status=%s response=%s",
                round_num + 1,
                e.response.status_code if e.response else None,
                getattr(e.response, "text", "")[:500] if e.response else None,
            )
            err_msg = str(e)
            if e.response and e.response.status_code == 404:
                if endpoint.is_ollama:
                    err_msg = (
                        "OLLAMA 404 at %s/api/chat. Check: (1) model_server_url "
                        "points to Ollama; (2) model '%s' exists (GET /api/tags); "
                        "(3) Ollama is running."
                    ) % (endpoint.base_url, use_model)
                else:
                    err_msg = (
                        "Model API 404 for %s at %s. Check provider_urls and "
                        "API key for %s."
                    ) % (use_model, endpoint.base_url, endpoint.provider)
            if total_prompt_tokens or total_eval_tokens:
                logger.info(
                    "chat_flow error_exit total_prompt_tokens=%s total_eval_tokens=%s",
                    total_prompt_tokens,
                    total_eval_tokens,
                )
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
            if total_prompt_tokens or total_eval_tokens:
                logger.info(
                    "chat_flow error_exit total_prompt_tokens=%s total_eval_tokens=%s",
                    total_prompt_tokens,
                    total_eval_tokens,
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
                "chat_flow done duration_sec=%.3f rounds=%s "
                "total_prompt=%s total_eval=%s total=%s",
                time.perf_counter() - t_flow_start,
                round_num + 1,
                total_prompt_tokens,
                total_eval_tokens,
                total_prompt_tokens + total_eval_tokens,
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
                    if tname == "help":
                        content_str = await _run_help_for_model(
                            proxy,
                            tool_registry,
                            args_dict,
                            representation,
                        )
                    else:
                        logger.debug(
                            "chat_flow session_tool server_id from registry: %s",
                            tname,
                        )
                        content_str = await _run_session_tool(
                            proxy,
                            tool_registry,
                            tname,
                            args_dict,
                            representation,
                        )
                else:
                    content_str = await _run_tool(
                        proxy,
                        tname,
                        args_dict,
                        representation=representation,
                    )
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
                content_str = representation.format_tool_result({"error": str(e)})
            history.append(_tool_message(tname, content_str))

    await proxy.close()
    logger.info(
        "chat_flow done duration_sec=%.3f rounds=%s",
        time.perf_counter() - t_flow_start,
        use_max_rounds,
    )
    last_content = history[-1].get("content", "") if history else ""
    return {"message": last_content, "history": history}
