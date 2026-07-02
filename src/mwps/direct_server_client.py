"""
Direct HTTP client to a single server (by server_url). Proxy is not used.

Used after resolving server_id -> server_url from proxy list_servers.
Calls: POST server_url/api/jsonrpc (command execution), GET server_url/commands (help).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, cast

import httpx

logger = logging.getLogger(__name__)

DIRECT_SERVER_TIMEOUT_SEC = 30.0


async def call_command(
    server_url: str,
    command: str,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Execute a command on the server directly (POST server_url/api/jsonrpc).

    Proxy is not involved. Use server_url from list_servers (proxy) first.
    """
    base = server_url.rstrip("/")
    url = f"{base}/api/jsonrpc"
    payload: Dict[str, Any] = {
        "jsonrpc": "2.0",
        "method": command,
        "params": params if params is not None else {},
        "id": 1,
    }
    try:
        async with httpx.AsyncClient(
            timeout=DIRECT_SERVER_TIMEOUT_SEC,
            verify=False,
        ) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:  # noqa: BLE001
        logger.warning("Direct call %s %s failed: %s", server_url, command, e)
        return {"error": str(e), "success": False}
    err = data.get("error")
    if err:
        return {"error": err.get("message", str(err)), "success": False}
    result = data.get("result", data)
    return cast(
        Dict[str, Any], result if isinstance(result, dict) else {"result": result}
    )


async def get_help(
    server_url: str,
    command: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get help from the server directly (GET server_url/commands).

    Returns full command list; if command is set, filters to that command info.
    Proxy is not involved.
    """
    base = server_url.rstrip("/")
    url = f"{base}/commands"
    try:
        async with httpx.AsyncClient(
            timeout=DIRECT_SERVER_TIMEOUT_SEC,
            verify=False,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:  # noqa: BLE001
        logger.warning("Direct help %s failed: %s", server_url, e)
        return {"error": str(e), "commands": []}
    commands: List[Dict[str, Any]] = data.get("commands") or data.get("tools") or data
    if not isinstance(commands, list):
        commands = []
    if command:
        for c in commands:
            if (c.get("name") or c.get("command") or "").strip() == command:
                return {"command": c, "commands": [c]}
        return {"command": None, "commands": []}
    return {"commands": commands}
