"""
MWPS context representation: serialize tools and messages for /api/chat.
Step 08.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Dict, List

from .command_schema import CommandSchema
from .context_representation import ContextRepresentation

if TYPE_CHECKING:
    from .representation_registry import RepresentationRegistry


class MwpsRepresentation(ContextRepresentation):
    """
    Serializes tools and messages for MWPS chat API.
    Tools: type "function", function { name, description, parameters }.
    Messages: role, content (and tool_calls / tool results per MWPS spec).
    """

    def serialize_tools(
        self,
        tool_list: List[tuple[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Convert (display_name, CommandSchema) list to MWPS tools array.
        """
        out: List[Dict[str, Any]] = []
        for display_name, item in tool_list:
            if isinstance(item, CommandSchema):
                desc = item.description or ""
                params = item.parameters if isinstance(item.parameters, dict) else {}
            else:
                desc = getattr(item, "description", "") or ""
                params = getattr(item, "parameters", None) or {}
                if not isinstance(params, dict):
                    params = {}
            out.append(
                {
                    "type": "function",
                    "function": {
                        "name": display_name,
                        "description": desc,
                        "parameters": params,
                    },
                }
            )
        return out

    def serialize_messages(
        self,
        messages: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Pass through or normalize to MWPS message shape (role, content).
        """
        result: List[Dict[str, Any]] = []
        for m in messages:
            if not isinstance(m, dict):
                continue
            msg: Dict[str, Any] = {}
            if "role" in m:
                msg["role"] = m["role"]
            if "content" in m:
                msg["content"] = m["content"]
            for key in ("tool_calls", "parts", "name"):
                if key in m and m[key] is not None:
                    msg[key] = m[key]
            if msg:
                result.append(msg)
        return result

    def format_tool_result(self, raw_result: Any) -> str:
        """
        Translate raw tool result to MWPS tool message content (JSON or str).
        """
        if isinstance(raw_result, dict):
            return json.dumps(raw_result)
        return str(raw_result)


def register_mwps_models(
    registry: "RepresentationRegistry",
    model_ids: List[str],
) -> None:
    """
    Register MwpsRepresentation for each model_id (e.g. from config mwps_models).
    One shared instance per registry.
    """
    rep = MwpsRepresentation()
    for mid in model_ids or []:
        if mid and str(mid).strip():
            registry.register(str(mid).strip(), rep)
