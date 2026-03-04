"""
Discover commands: list_servers from proxy; schemas from proxy response or server.

When proxy list_servers (e.g. GET /list) returns commands per server, we use them.
Otherwise we fetch from each server (GET server_url/commands). Step 03.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx

from .command_schema import CommandSchema
from .proxy_client import ProxyClient, ProxyClientError
from .server_resolver import extract_servers_list

logger = logging.getLogger(__name__)

# Timeout for direct server fetches (GET server_url/commands).
DIRECT_SERVER_TIMEOUT_SEC = 15.0

# Command id format: command_name.server_id (e.g. echo.ollama-adapter)
COMMAND_ID_SEP = "."


def make_command_id(command_name: str, server_id: str) -> str:
    """Build canonical command id from command name and server id."""
    return "%s%s%s" % (command_name, COMMAND_ID_SEP, server_id)


def parse_command_id(command_id: str) -> Tuple[str, str]:
    """Split command_id into (command_name, server_id). Last dot separates."""
    idx = command_id.rfind(COMMAND_ID_SEP)
    if idx < 0:
        return (command_id, "")
    return (command_id[:idx], command_id[idx + 1 :])


def _commands_dict_to_list(commands_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert proxy-style commands dict to list for _parse_command.
    Proxy /list returns commands: { "echo": { "summary": "...", "parameters": {} } }.
    """
    out: List[Dict[str, Any]] = []
    for name, info in commands_dict.items():
        if not name or not isinstance(info, dict):
            continue
        desc = (info.get("summary") or info.get("description") or "").strip()
        params = info.get("parameters") or info.get("params") or {}
        if not isinstance(params, dict):
            params = {}
        out.append({"name": name, "description": desc, "parameters": params})
    return out


class CommandDiscovery:
    """
    Fetches list_servers and per-server command schemas; builds flat list.
    On refresh failure for a server, marks that server's commands unavailable.
    """

    def __init__(
        self,
        proxy_client: ProxyClient,
        discovery_interval_sec: int = 0,
    ) -> None:
        """
        Initialize discovery.

        Args:
            proxy_client: Client for list_servers only (schemas fetched from servers).
            discovery_interval_sec: 0 = no periodic refresh; >0 = interval in seconds.
        """
        self._proxy = proxy_client
        self._interval = max(0, discovery_interval_sec)
        self._cache: List[Tuple[str, CommandSchema, bool]] = []
        self._unavailable_servers: set[str] = set()

    async def refresh(self) -> None:
        """
        Fetch list_servers from proxy; per-server commands from each server directly.
        On server failure: mark that server's commands unavailable, keep in list.
        """
        try:
            raw = await self._proxy.list_servers()
        except ProxyClientError as e:
            logger.warning("Command discovery: list_servers failed: %s", e.message)
            return
        servers = extract_servers_list(raw)
        if not servers:
            return
        new_cache: List[Tuple[str, CommandSchema, bool]] = []
        suffix = COMMAND_ID_SEP
        for srv in servers:
            if not isinstance(srv, dict):
                continue
            server_id = (srv.get("server_id") or srv.get("id") or "").strip()
            if not server_id:
                continue
            server_url = (srv.get("server_url") or srv.get("url") or "").strip()
            if not server_url:
                logger.warning(
                    "Command discovery: server %s has no server_url, skipping",
                    server_id,
                )
                continue
            # Prefer commands from proxy (e.g. GET /list); else fetch from server.
            commands_raw = srv.get("commands")
            if isinstance(commands_raw, dict):
                commands = _commands_dict_to_list(commands_raw)
            else:
                commands = await self._fetch_commands_from_server(server_url)
            start_len = len(new_cache)
            try:
                for cmd in commands or []:
                    cid, schema = self._parse_command(cmd, server_id)
                    if cid and schema:
                        new_cache.append((cid, schema, True))
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "Command discovery: server %s failed: %s",
                    server_id,
                    str(e),
                )
                self._unavailable_servers.add(server_id)
                for i in range(start_len, len(new_cache)):
                    cid, schema, _ = new_cache[i]
                    if cid.endswith(suffix + server_id):
                        new_cache[i] = (cid, schema, False)
                for cid, schema, _ in self._cache:
                    if cid.endswith(suffix + server_id):
                        new_cache.append((cid, schema, False))
            if len(new_cache) == start_len:
                for cid, schema, _ in self._cache:
                    if cid.endswith(suffix + server_id):
                        new_cache.append((cid, schema, False))
                if any(cid.endswith(suffix + server_id) for cid, _, _ in self._cache):
                    self._unavailable_servers.add(server_id)
        self._cache = new_cache

    def _parse_command(
        self,
        cmd: Any,
        server_id: str,
    ) -> Tuple[Optional[str], Optional[CommandSchema]]:
        """Build (command_id, CommandSchema) from one command dict."""
        if not isinstance(cmd, dict):
            return (None, None)
        name = (cmd.get("name") or cmd.get("command") or "").strip()
        if not name:
            return (None, None)
        desc = (cmd.get("description") or cmd.get("summary") or "").strip()
        params = cmd.get("parameters") or cmd.get("params") or {}
        if not isinstance(params, dict):
            params = {}
        try:
            schema = CommandSchema(name=name, description=desc, parameters=params)
        except ValueError:
            return (None, None)
        cid = make_command_id(name, server_id)
        return (cid, schema)

    async def _fetch_commands_from_server(
        self, server_url: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch command list directly from server (GET server_url/commands).
        Proxy is not used; only list_servers goes to the proxy.
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
            logger.warning("Command discovery: direct fetch %s failed: %s", url, str(e))
            return []
        commands = data.get("commands") or data.get("tools") or data
        if isinstance(commands, list):
            return commands
        return []

    def get_discovered_commands(
        self,
        available_only: bool = False,
    ) -> List[Tuple[str, CommandSchema, bool]]:
        """
        Return cached list of (command_id, CommandSchema, available).
        If available_only=True, only entries with available=True.
        """
        if available_only:
            return [(cid, s, a) for cid, s, a in self._cache if a]
        return list(self._cache)
