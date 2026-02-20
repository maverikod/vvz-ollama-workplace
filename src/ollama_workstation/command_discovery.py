"""
Discover commands from proxy: list_servers, per-server schemas, flat list.
Startup + optional periodic refresh; mark unavailable when server down; step 03.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from .command_schema import CommandSchema
from .proxy_client import ProxyClient, ProxyClientError

logger = logging.getLogger(__name__)

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
    return (command_id[:idx], command_id[idx + 1:])


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
            proxy_client: Client for list_servers and help.
            discovery_interval_sec: 0 = no periodic refresh; >0 = interval in seconds.
        """
        self._proxy = proxy_client
        self._interval = max(0, discovery_interval_sec)
        self._cache: List[Tuple[str, CommandSchema, bool]] = []
        self._unavailable_servers: set[str] = set()

    async def refresh(self) -> None:
        """
        Fetch list_servers and per-server commands; update cache.
        On server failure: mark that server's commands unavailable, keep in list.
        """
        try:
            raw = await self._proxy.list_servers()
        except ProxyClientError as e:
            logger.warning("Command discovery: list_servers failed: %s", e.message)
            return
        servers = raw.get("servers") or raw.get("items") or []
        if not isinstance(servers, list):
            logger.warning("Command discovery: servers not a list")
            return
        new_cache: List[Tuple[str, CommandSchema, bool]] = []
        suffix = COMMAND_ID_SEP
        for srv in servers:
            if not isinstance(srv, dict):
                continue
            server_id = (srv.get("server_id") or srv.get("id") or "").strip()
            if not server_id:
                continue
            commands = srv.get("commands")
            if not isinstance(commands, list):
                help_commands = await self._fetch_commands_via_help(server_id)
                commands = help_commands if isinstance(help_commands, list) else []
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

    async def _fetch_commands_via_help(self, server_id: str) -> List[Dict[str, Any]]:
        """Call proxy help(server_id) and return list of command dicts if any."""
        try:
            out = await self._proxy.help(server_id=server_id)
        except ProxyClientError:
            return []
        commands = out.get("commands") or out.get("tools") or []
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
