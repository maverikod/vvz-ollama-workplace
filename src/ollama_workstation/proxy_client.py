"""
Thin client for MCP Proxy: list_servers, call_server, help.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, cast
from urllib.parse import urlparse

from .config import WorkstationConfig

logger = logging.getLogger(__name__)


def _parse_proxy_url(proxy_url: str) -> tuple[str, str, int]:
    """Return (protocol, host, port) from proxy base URL."""
    parsed = urlparse(proxy_url)
    scheme = parsed.scheme or "http"
    host = parsed.hostname or "localhost"
    port = parsed.port
    if port is None:
        port = 443 if scheme == "https" else 80
    protocol = "https" if scheme == "https" else "http"
    return (protocol, host, port)


class ProxyClientError(Exception):
    """Raised when a proxy call fails; message is safe to put in tool result content."""

    def __init__(self, message: str, status: Optional[int] = None) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


class ProxyClient:
    """
    Client that calls the MCP Proxy for list_servers, call_server, and help.

    Uses adapter JsonRpcClient when proxy speaks JSON-RPC. On failure
    raises ProxyClientError so chat flow can put the error in tool content.
    """

    def __init__(self, config: WorkstationConfig) -> None:
        self._config = config
        self._client: Any = None

    async def _get_client(self) -> Any:
        """Lazy-create JsonRpcClient for the proxy (reuse adapter client)."""
        if self._client is not None:
            return self._client
        try:
            from mcp_proxy_adapter.client.jsonrpc_client import JsonRpcClient
        except ImportError as e:
            raise ProxyClientError(
                f"MCP Proxy Adapter client not available: {e}"
            ) from e
        protocol, host, port = _parse_proxy_url(self._config.mcp_proxy_url)
        self._client = JsonRpcClient(
            protocol=protocol,
            host=host,
            port=port,
            token_header=self._config.proxy_token_header,
            token=self._config.proxy_token,
            timeout=30.0,
        )
        return self._client

    async def _call(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Execute JSON-RPC method on proxy; return result or raise ProxyClientError."""
        params = params or {}
        try:
            client = await self._get_client()
            response = await client.jsonrpc_call(method, params)
            return cast(Dict[str, Any], client._extract_result(response))
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            status = getattr(e, "status_code", None) or getattr(
                e, "status", None
            )
            logger.warning("Proxy call %s failed: %s", method, msg)
            raise ProxyClientError(msg, status=status) from e

    async def list_servers(
        self,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        filter_enabled: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """List servers registered in the MCP Proxy.

        Args:
            page: Optional page number (pagination).
            page_size: Optional page size.
            filter_enabled: Optional filter for enabled only.

        Returns:
            Proxy response (e.g. dict with "servers" or similar).
        """
        params: Dict[str, Any] = {}
        if page is not None:
            params["page"] = page
        if page_size is not None:
            params["page_size"] = page_size
        if filter_enabled is not None:
            params["filter_enabled"] = filter_enabled
        return cast(Dict[str, Any], await self._call("list_servers", params))

    async def call_server(
        self,
        server_id: str,
        command: str,
        copy_number: Optional[int] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a command on a registered server.

        Args:
            server_id: Server identifier from list_servers.
            command: Command name to run.
            copy_number: Optional; default 1.
            params: Optional command parameters.

        Returns:
            Proxy response (command result).
        """
        payload: Dict[str, Any] = {
            "server_id": server_id,
            "command": command,
        }
        if copy_number is not None:
            payload["copy_number"] = copy_number
        if params is not None:
            payload["params"] = params
        return cast(Dict[str, Any], await self._call("call_server", payload))

    async def help(
        self,
        server_id: str,
        copy_number: Optional[int] = None,
        command: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get help for a server or a specific command.

        Args:
            server_id: Server identifier from list_servers.
            copy_number: Optional; default 1.
            command: Optional command name for command-specific help.

        Returns:
            Proxy response (help text or structure).
        """
        payload: Dict[str, Any] = {"server_id": server_id}
        if copy_number is not None:
            payload["copy_number"] = copy_number
        if command is not None:
            payload["command"] = command
        return cast(Dict[str, Any], await self._call("help", payload))

    async def close(self) -> None:
        """Close the underlying HTTP client if any."""
        if self._client is not None:
            if hasattr(self._client, "close"):
                await self._client.close()
            self._client = None
