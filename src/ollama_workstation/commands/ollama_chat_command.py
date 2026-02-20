"""
Adapter Command: ollama_chat — chat with OLLAMA using MCP Proxy tools.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import logging
import os
import time
import uuid as uuid_module
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import redis
from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult

from ..chat_flow import run_chat_flow
from ..command_alias_registry import CommandAliasRegistry
from ..command_discovery import CommandDiscovery
from ..config import load_config
from ..context_builder import ContextBuilder, ContextBuilderError
from ..context_file_loader import load_tools_json
from ..effective_tool_list_builder import EffectiveToolListBuilder
from ..message_source import MessageSource
from ..proxy_client import ProxyClient
from ..safe_name_translator import SafeNameTranslator
from ..message_store import RedisMessageStore
from ..tool_call_registry import ToolCallRegistry
from ..message_stream_writer import MessageStreamWriter
from ..ollama_representation import OllamaRepresentation
from ..redis_message_record import RedisMessageRecord
from ..representation_registry import RepresentationRegistry
from ..relevance_slot_builder import RelevanceSlotBuilder
from .ollama_chat_schema import (
    get_ollama_chat_error_schema,
    get_ollama_chat_metadata,
    get_ollama_chat_params_schema,
    get_ollama_chat_result_schema,
)
from .session_init_command import _get_session_store

logger = logging.getLogger(__name__)

# Default adapter config path when config_path not passed (e.g. in Docker)
_DEFAULT_CONFIG_PATH = os.environ.get(
    "ADAPTER_CONFIG_PATH", "/app/config/adapter_config.json"
)


class OllamaChatCommand(Command):
    """
    Run a chat with OLLAMA where the model can use MCP Proxy tools
    (list_servers, call_server, help). Accepts messages and optional model,
    stream, max_tool_rounds. Returns the final assistant message and
    optionally the full message history.
    """

    name = "ollama_chat"
    descr = (
        "Run a chat turn with OLLAMA: send messages, get assistant reply. The model "
        "has access to MCP Proxy tools (list_servers, call_server, help) and can call "
        "any server in the proxy. Optional: model, stream, max_tool_rounds. "
        "Returns final message and full message history."
    )

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """
        Get JSON schema for command parameters.

        Returns:
            JSON schema with descriptions and examples (params in metadata).
        """
        return get_ollama_chat_params_schema()

    @classmethod
    def get_result_schema(cls) -> Dict[str, Any]:
        """
        Get JSON schema for successful result structure.

        Returns:
            JSON schema for success response.
        """
        return get_ollama_chat_result_schema()

    @classmethod
    def get_error_schema(cls) -> Dict[str, Any]:
        """
        Get JSON schema for error result structure.

        Returns:
            JSON schema for error response.
        """
        return get_ollama_chat_error_schema()

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """
        Get complete metadata for the command (name, description, params,
        result_schema, error_schema, error_codes, examples).

        Returns:
            Complete command metadata dictionary.
        """
        return get_ollama_chat_metadata(
            name=cls.name,
            description=(cls.__doc__ or cls.descr or "").strip(),
        )

    async def execute(
        self,
        messages: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        stream: bool = False,
        max_tool_rounds: Optional[int] = None,
        config_path: Optional[str] = None,
        session_id: Optional[str] = None,
        content: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """
        Load config, run chat flow. With session_id + content: load history from
        store, build context, run chat, persist user message and reply.
        Otherwise require messages and run as before.
        """
        path_to_load: Optional[str] = config_path
        if path_to_load is None and Path(_DEFAULT_CONFIG_PATH).exists():
            path_to_load = _DEFAULT_CONFIG_PATH
        t_exec_start = time.perf_counter()
        logger.info(
            "ollama_chat execute session_id=%s content_len=%s messages_count=%s",
            session_id or None,
            len(str(content)) if content else 0,
            len(messages) if messages else 0,
        )
        try:
            t0 = time.perf_counter()
            config = load_config(path_to_load)
            logger.info(
                "ollama_chat config_load duration_sec=%.3f", time.perf_counter() - t0
            )
        except ValueError as e:
            logger.warning("ollama_chat config load ValueError: %s", e)
            return ErrorResult(message=str(e), code=-32602)
        except Exception as e:  # noqa: BLE001
            logger.exception("ollama_chat config load failed: %s", e)
            return ErrorResult(message=f"Config load failed: {e}", code=-32603)

        tools_from_file: Optional[List[Dict[str, Any]]] = None
        if getattr(config, "tools_file_path", None):
            tools_from_file = load_tools_json(config.tools_file_path)
        if session_id and (content is not None and str(content).strip()):
            return await self._execute_session_mode(
                config=config,
                session_id=(session_id or "").strip(),
                content=str(content).strip(),
                model=model,
                stream=stream,
                max_tool_rounds=max_tool_rounds,
                config_path=path_to_load,
                tools_from_file=tools_from_file,
            )
        if messages and len(messages) > 0:
            result = await run_chat_flow(
                config=config,
                messages=messages,
                model=model,
                stream=stream,
                max_tool_rounds=max_tool_rounds,
                tools_from_file=tools_from_file,
            )
        else:
            return ErrorResult(
                message=(
                    "Provide either messages (non-empty list) or "
                    "session_id and content."
                ),
                code=-32602,
            )
        if result.get("error"):
            logger.warning("ollama_chat run_chat_flow error: %s", result["error"])
            return ErrorResult(
                message=result["error"],
                code=-32603,
            )
        logger.info(
            "ollama_chat execute done duration_sec=%.3f",
            time.perf_counter() - t_exec_start,
        )
        return SuccessResult(
            data={
                "message": result.get("message", ""),
                "history": result.get("history", []),
            },
        )

    async def _execute_session_mode(
        self,
        config: Any,
        session_id: str,
        content: str,
        model: Optional[str] = None,
        stream: bool = False,
        max_tool_rounds: Optional[int] = None,
        config_path: Optional[str] = None,
        tools_from_file: Optional[List[Dict[str, Any]]] = None,
    ) -> Any:
        """Load session and history from store, run chat, persist user + reply."""
        t_session_start = time.perf_counter()
        logger.info("ollama_chat session_mode session_id=%s", session_id)
        t0 = time.perf_counter()
        store = _get_session_store(config_path)
        session = store.get(session_id)
        logger.info(
            "ollama_chat session_load duration_sec=%.3f", time.perf_counter() - t0
        )
        if session is None:
            logger.warning("ollama_chat session not found: %s", session_id)
            return ErrorResult(
                message="Session not found: %s" % session_id, code=-32602
            )
        use_model = model or session.model or config.ollama_model
        logger.debug("ollama_chat session loaded model=%s", use_model)

        try:
            redis_client = redis.Redis(
                host=config.redis_host,
                port=config.redis_port,
                password=config.redis_password or None,
                decode_responses=False,
            )
        except Exception as e:  # noqa: BLE001
            logger.exception("ollama_chat Redis connection failed: %s", e)
            return ErrorResult(
                message="Redis connection failed: %s" % e,
                code=-32603,
            )
        message_store = RedisMessageStore(
            redis_client,
            key_prefix=config.redis_key_prefix,
        )
        # Form context: trim, last_n, relevance slot, then append current message.
        registry = RepresentationRegistry(default=OllamaRepresentation())
        relevance_builder = RelevanceSlotBuilder(
            mode=getattr(config, "relevance_slot_mode", "fixed_order") or "fixed_order"
        )
        context_builder = ContextBuilder(
            session_store=store,
            representation_registry=registry,
            message_store=message_store,
            relevance_slot_builder=relevance_builder,
            model_context_tokens=getattr(config, "max_context_tokens", None),
            standards_file_path=getattr(config, "standards_file_path", None) or None,
            rules_file_path=getattr(config, "rules_file_path", None) or None,
        )
        current_message = {"role": "user", "content": content}
        try:
            t0 = time.perf_counter()
            _trimmed, serialized = context_builder.build(
                session_id=session_id,
                current_message=current_message,
                max_context_tokens=getattr(config, "max_context_tokens", 4096),
                last_n_messages=getattr(config, "last_n_messages", 10),
                min_semantic_tokens=getattr(config, "min_semantic_tokens", 256),
                min_documentation_tokens=getattr(config, "min_documentation_tokens", 0),
                model_override=use_model,
            )
            history = serialized + [current_message]
            logger.info(
                "ollama_chat context_build duration_sec=%.3f history_len=%s",
                time.perf_counter() - t0,
                len(history),
            )
        except ContextBuilderError as e:
            logger.warning("ollama_chat context_builder failed, using fallback: %s", e)
            # Fallback: all messages from store + current (no trim/slots).
            raw = message_store.get_messages(session_id)
            history = [
                {
                    "role": (m.get("source") or "user"),
                    "content": (m.get("body") or ""),
                }
                for m in raw
            ]
            history.append(current_message)

        # Session tools only: model sees session list; no proxy/server_id.
        session_tools_ollama: Optional[List[Dict[str, Any]]] = None
        tool_registry = None
        try:
            proxy_for_discovery = ProxyClient(config)
            discovery = CommandDiscovery(
                proxy_for_discovery,
                discovery_interval_sec=getattr(
                    config, "command_discovery_interval_sec", 0
                ),
            )
            await discovery.refresh()
            discovered = discovery.get_discovered_commands(available_only=False)
            builder = EffectiveToolListBuilder(
                CommandAliasRegistry(),
                SafeNameTranslator(),
            )
            _tool_list, tool_registry = builder.build(
                session,
                getattr(config, "commands_policy_config", None),
                discovered,
            )
            session_tools_ollama = OllamaRepresentation().serialize_tools(_tool_list)
        except Exception as e:  # noqa: BLE001
            session_tools_ollama = []
            tool_registry = ToolCallRegistry()
            logger.warning(
                "ollama_chat session_tools_build_failed session_id=%s error=%s",
                session_id,
                e,
                exc_info=True,
            )

        logger.info(
            "ollama_chat run_chat_flow session_id=%s history_len=%s",
            session_id,
            len(history),
        )
        t0 = time.perf_counter()
        result = await run_chat_flow(
            config=config,
            messages=history,
            model=use_model,
            stream=stream,
            max_tool_rounds=max_tool_rounds,
            session_tools=session_tools_ollama,
            tool_registry=tool_registry,
            tools_from_file=tools_from_file,
        )
        logger.info(
            "ollama_chat chat_flow duration_sec=%.3f",
            time.perf_counter() - t0,
        )
        if result.get("error"):
            logger.warning(
                "ollama_chat session_mode chat_flow error session_id=%s: %s",
                session_id,
                result["error"],
            )
            return ErrorResult(
                message=result["error"],
                code=-32603,
            )

        reply = result.get("message") or ""
        now = datetime.now(timezone.utc).isoformat()
        writer = MessageStreamWriter(
            redis_client,
            key_prefix=config.redis_key_prefix,
        )
        try:
            t0 = time.perf_counter()
            writer.write(
                RedisMessageRecord(
                    uuid=str(uuid_module.uuid4()),
                    created_at=now,
                    source=MessageSource.USER,
                    body=content,
                    session_id=session_id,
                )
            )
            writer.write(
                RedisMessageRecord(
                    uuid=str(uuid_module.uuid4()),
                    created_at=now,
                    source=MessageSource.MODEL,
                    body=reply,
                    session_id=session_id,
                )
            )
            logger.info(
                "ollama_chat persist duration_sec=%.3f",
                time.perf_counter() - t0,
            )
        except Exception as e:  # noqa: BLE001
            logger.exception(
                "ollama_chat persist_messages_failed session_id=%s: %s",
                session_id,
                e,
            )
            return ErrorResult(
                message="Failed to persist messages: %s" % e,
                code=-32603,
            )
        logger.info(
            "ollama_chat session_mode done duration_sec=%.3f",
            time.perf_counter() - t_session_start,
        )
        return SuccessResult(
            data={
                "message": reply,
                "history": result.get("history", []),
            },
        )
