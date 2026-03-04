"""
Adapter command: get_model_context — return what would be sent to the model.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import redis
from mcp_proxy_adapter.commands.base import Command
from mcp_proxy_adapter.commands.result import SuccessResult, ErrorResult

from ..command_alias_registry import CommandAliasRegistry
from ..command_discovery import CommandDiscovery
from ..config import load_config
from ..model_loading_state import get_active_model
from ..context_builder import ContextBuilder, ContextBuilderError
from ..context_file_loader import load_tools_json
from ..effective_tool_list_builder import EffectiveToolListBuilder
from ..message_store import RedisMessageStore
from ..ollama_representation import OllamaRepresentation, register_ollama_models
from ..proxy_client import ProxyClient
from ..representation_registry import RepresentationRegistry
from ..relevance_slot_builder import RelevanceSlotBuilder
from ..safe_name_translator import SafeNameTranslator
from ..vectorization_client import DirectEmbedVectorizationClient
from ..tools import MODEL_HELP_TOOL
from .session_init_command import _get_session_store

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_PATH = os.environ.get(
    "ADAPTER_CONFIG_PATH", "/app/config/adapter_config.json"
)


def _messages_for_display(
    messages: List[Dict[str, Any]], max_content: int = 2000
) -> List[Dict[str, Any]]:
    """Return messages with content truncated for display."""
    out = []
    for m in messages:
        role = m.get("role", "?")
        content = (m.get("content") or "").strip()
        preview = content[:max_content] + ("..." if len(content) > max_content else "")
        out.append(
            {"role": role, "content_preview": preview, "content_len": len(content)}
        )
    return out


class GetModelContextCommand(Command):
    """
    Return the exact final context sent to the model (no intermediate data).

    Same pipeline as ollama_chat: messages and tools are serialized via the
    representation layer for the session's model (RepresentationRegistry).
    Tools from discovery (deduped by command name); final shape is
    model-specific (e.g. OllamaRepresentation for OLLAMA models).
    """

    name = "get_model_context"
    descr = (
        "Return the exact final context sent to the model: messages and tools "
        "as in the OLLAMA request. Params: session_id (required), "
        "content (optional user message to append). Shows end result only."
    )

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Parameters: session_id (required), content (optional)."""
        return {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": (
                        "Session UUID4 returned by session_init. The context is "
                        "built for this session (its standards, session_rules, "
                        "and message history from store)."
                    ),
                    "example": "4d86c036-b5f0-435e-ac4b-f1f56d765769",
                },
                "content": {
                    "type": "string",
                    "description": (
                        "Optional user message text to append as the last message, "
                        "as ollama_chat does when you pass content. If omitted, "
                        "a placeholder '(no content)' is used for the last message."
                    ),
                    "example": "What is 2+2?",
                },
            },
            "required": ["session_id"],
            "additionalProperties": False,
        }

    @classmethod
    def get_result_schema(cls) -> Dict[str, Any]:
        """Success result: exact final context (messages + tools) as sent to model."""
        return {
            "type": "object",
            "properties": {
                "final_context": {
                    "type": "string",
                    "description": (
                        "Always 'exact_final': this response is the exact final "
                        "context (messages + tools) as sent to the model."
                    ),
                },
                "representation_model": {
                    "type": "string",
                    "description": (
                        "Model id used to select representation (session.model or "
                        "config); messages and tools are serialized for this model."
                    ),
                },
                "messages": {
                    "type": "array",
                    "description": (
                        "Final message list sent to the model. Each item has "
                        "role, content_preview (truncated), content_len."
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "role": {
                                "type": "string",
                                "description": "Role: system, user, or assistant",
                            },
                            "content_preview": {
                                "type": "string",
                                "description": "Content truncated for display",
                            },
                            "content_len": {
                                "type": "integer",
                                "description": "Full content length in characters",
                            },
                        },
                    },
                },
                "tool_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Final tool names sent to the model (deduped by command name)."
                    ),
                },
                "tools": {
                    "type": "array",
                    "description": (
                        "Final tool definitions sent to the model: name (command name "
                        "only), description, parameters. One per command name."
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "parameters": {"type": "object"},
                        },
                    },
                },
                "messages_count": {
                    "type": "integer",
                    "description": "Total number of messages in the context",
                },
            },
            "required": [
                "final_context",
                "representation_model",
                "messages",
                "tool_names",
                "tools",
                "messages_count",
            ],
        }

    @classmethod
    def get_error_schema(cls) -> Dict[str, Any]:
        """Error result: message (string)."""
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Human-readable error message",
                },
            },
        }

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Complete metadata: name, description, schemas, error_codes, examples."""
        return {
            "name": cls.name,
            "description": (cls.__doc__ or cls.descr or "").strip(),
            "params_schema": cls.get_schema(),
            "result_schema": cls.get_result_schema(),
            "error_schema": cls.get_error_schema(),
            "error_codes": [
                {
                    "code": -32602,
                    "description": "Invalid parameters or session not found",
                    "when": (
                        "session_id missing, session not found, or context "
                        "build failed (e.g. model not set for session)."
                    ),
                },
                {
                    "code": -32603,
                    "description": "Internal error",
                    "when": "Config load failed or Redis connection failed",
                },
            ],
            "examples": {
                "success": {
                    "success": True,
                    "data": {
                        "final_context": "exact_final",
                        "representation_model": "llama3.2",
                        "messages": [
                            {
                                "role": "system",
                                "content_preview": "Reply in one sentence.",
                                "content_len": 22,
                            },
                            {
                                "role": "user",
                                "content_preview": "What is 2+2?",
                                "content_len": 11,
                            },
                        ],
                        "tool_names": ["embed", "echo"],
                        "tools": [
                            {"name": "embed", "description": "..."},
                            {"name": "echo", "description": "..."},
                        ],
                        "messages_count": 2,
                    },
                },
                "error_not_found": {
                    "success": False,
                    "error": {
                        "code": -32602,
                        "message": "Session not found: abc-123",
                    },
                },
            },
        }

    async def execute(
        self,
        parameters: Optional[Dict[str, Any]] = None,
        config_path: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        params = dict(parameters or {})
        for key in ("session_id", "content"):
            if key in kwargs and kwargs[key] is not None:
                params[key] = kwargs[key]
        session_id = (params.get("session_id") or "").strip()
        if not session_id:
            return ErrorResult(message="session_id is required", code=-32602)
        content = (params.get("content") or "").strip()
        default_exists = Path(_DEFAULT_CONFIG_PATH).exists()
        path = config_path or (_DEFAULT_CONFIG_PATH if default_exists else None)
        try:
            config = load_config(path)
        except Exception as e:  # noqa: BLE001
            logger.warning("get_model_context config load failed: %s", e)
            return ErrorResult(message=str(e), code=-32603)
        store = _get_session_store(config_path)
        session = store.get(session_id)
        if session is None:
            return ErrorResult(
                message="Session not found: %s" % session_id, code=-32602
            )
        use_model = session.model or get_active_model() or config.ollama_model
        try:
            redis_client = redis.Redis(
                host=config.redis_host,
                port=config.redis_port,
                password=config.redis_password or None,
                decode_responses=False,
            )
        except Exception as e:  # noqa: BLE001
            return ErrorResult(message="Redis failed: %s" % e, code=-32603)
        message_store = RedisMessageStore(
            redis_client,
            key_prefix=config.redis_key_prefix,
        )
        registry = RepresentationRegistry(default=OllamaRepresentation())
        register_ollama_models(registry, getattr(config, "ollama_models", None) or [])
        proxy_for_embed = ProxyClient(config)
        embed_client = DirectEmbedVectorizationClient(
            proxy_for_embed,
            config,
            embedding_server_id=getattr(
                config, "embedding_server_id", "embedding-service"
            ),
            embedding_command=getattr(config, "embedding_command", "embed"),
        )
        relevance_builder = RelevanceSlotBuilder(
            message_store=message_store,
            mode=getattr(config, "relevance_slot_mode", "fixed_order") or "fixed_order",
            vectorization_client=embed_client,
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
        current_message = {"role": "user", "content": content or "(no content)"}
        try:
            _trimmed, serialized = await context_builder.build(
                session_id=session_id,
                current_message=current_message,
                max_context_tokens=getattr(config, "max_context_tokens", 4096),
                last_n_messages=getattr(config, "last_n_messages", 10),
                min_semantic_tokens=getattr(config, "min_semantic_tokens", 256),
                min_documentation_tokens=getattr(config, "min_documentation_tokens", 0),
                model_override=use_model,
            )
            messages = serialized + [current_message]
        except ContextBuilderError as e:
            return ErrorResult(message=str(e), code=-32602)
        tools_raw: List[Dict[str, Any]] = []
        if getattr(config, "mcp_proxy_url", None):
            try:
                proxy_for_discovery = ProxyClient(config)
                discovery = CommandDiscovery(
                    proxy_for_discovery,
                    discovery_interval_sec=getattr(
                        config, "command_discovery_interval_sec", 0
                    ),
                )
                await discovery.refresh()
                await proxy_for_discovery.close()
                discovered = discovery.get_discovered_commands(available_only=False)
                builder = EffectiveToolListBuilder(
                    CommandAliasRegistry(),
                    SafeNameTranslator(),
                )
                _tool_list, _registry = builder.build(
                    session,
                    config.commands_policy_config,
                    discovered,
                    preferred_server_id=getattr(config, "adapter_server_id", None)
                    or None,
                )
                representation = registry.get_representation(use_model)
                session_tools = representation.serialize_tools(_tool_list)
                if session_tools:
                    tools_raw = list(session_tools)
                    tools_raw.append(MODEL_HELP_TOOL)
            except Exception as e:  # noqa: BLE001
                logger.debug(
                    "get_model_context discovery path failed, using fallback: %s", e
                )
        # Model gets only server-originated tools; never list_servers/call_server/help.
        if not tools_raw:
            tools_from_file = load_tools_json(getattr(config, "tools_file_path", None))
            if tools_from_file:
                for t in tools_from_file:
                    if t and isinstance(t, dict):
                        tools_raw.append(t)
            if not tools_raw:
                tools_raw = [MODEL_HELP_TOOL]
        has_help = any(
            ((t or {}).get("function") or {}).get("name") == "help"
            for t in (tools_raw or [])
        )
        if not has_help:
            tools_raw = list(tools_raw or [])
            tools_raw.append(MODEL_HELP_TOOL)
        tool_names = []
        tools_for_display: List[Dict[str, Any]] = []
        for t in tools_raw:
            fn = (t or {}).get("function") or {}
            name = fn.get("name")
            if name:
                tool_names.append(name)
                desc = (fn.get("description") or "").strip()
                tool_params = fn.get("parameters")
                tools_for_display.append(
                    {
                        "name": name,
                        "description": desc,
                        "parameters": (
                            tool_params if isinstance(tool_params, dict) else None
                        ),
                    }
                )
        display = _messages_for_display(messages)
        return SuccessResult(
            data={
                "final_context": "exact_final",
                "representation_model": use_model,
                "messages": display,
                "tool_names": tool_names,
                "tools": tools_for_display,
                "messages_count": len(messages),
            }
        )
