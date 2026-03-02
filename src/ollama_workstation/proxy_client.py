"""
Thin wrapper over mcp-proxy-adapter client for MCP Proxy.

All proxy access is via mcp_proxy_adapter.client.jsonrpc_client.JsonRpcClient:
build adapter params from config, create one client, all calls through adapter
(list_servers via REST GET /list when available, then JSON-RPC list_servers;
call_server and help via adapter JSON-RPC). No duplicate protocol logic.

WS Transport Contract (ws-contract-v1, see NAMING_FREEZE.md):
- When the adapter and proxy support WebSocket (mcp_proxy_url is wss://), the
  client uses a WS-first path: attempt JSON-RPC over the adapter's bidirectional
  WS channel (/ws) first; on connection failure, timeout, or non-JSON-RPC
  response, fall back to HTTP JSON-RPC.
- Fallback policy: WS attempt is best-effort; any exception in the WS path
  triggers immediate fallback to HTTP. No retries of WS within the same request.
- The same contract applies to model-workspace and database client pairs:
  aligned WS endpoint scheme (ws:// / wss://), single request/response over
  channel when supported, and explicit HTTP fallback.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, cast
from urllib.parse import urlparse

from .config import WorkstationConfig

logger = logging.getLogger(__name__)

# WS contract identifier; must match NAMING_FREEZE.md (backward-compatible v1).
WS_CONTRACT_VERSION = "ws-contract-v1"


def config_to_adapter_params(config: WorkstationConfig) -> Dict[str, Any]:
    """
    Build adapter JsonRpcClient parameters from workstation config (embed-client style).

    Supports http, https, ws, wss. For wss:// and ws:// the adapter uses the same
    host/port and derives ws_url (wss:// or ws://) for the WS channel; protocol
    is set to https for wss and http for ws so that TLS and ws_url match.

    Returns dict: protocol, host, port, token_header, token, cert, key, ca,
    check_hostname, timeout. Used to create a single JsonRpcClient instance.
    """
    parsed = urlparse((config.mcp_proxy_url or "").rstrip("/"))
    scheme = (parsed.scheme or "http").lower()
    host = parsed.hostname or "localhost"
    port = parsed.port
    if port is None:
        if scheme == "https" or scheme == "wss":
            port = 443
        else:
            port = 80
    # Adapter expects protocol "http" or "https"; wss -> https so ws_url is wss://
    protocol = "https" if scheme in ("https", "wss") else "http"
    params: Dict[str, Any] = {
        "protocol": protocol,
        "host": host,
        "port": port,
        "token_header": config.proxy_token_header,
        "token": config.proxy_token,
        "timeout": 30.0,
    }
    cert = getattr(config, "proxy_client_cert", None)
    key = getattr(config, "proxy_client_key", None)
    if cert and key:
        params["cert"] = cert
        params["key"] = key
        params["ca"] = getattr(config, "proxy_ca_cert", None)
    return params


class ProxyClientError(Exception):
    """Proxy call failed; message is safe to put in tool result content."""

    def __init__(self, message: str, status: Optional[int] = None) -> None:
        """Store error message and optional HTTP status for tool result."""
        super().__init__(message)
        self.message = message
        self.status = status


class ProxyClient:
    """
    Client for MCP Proxy: list_servers only (proxy acts as DNS).

    Uses mcp_proxy_adapter JsonRpcClient with params from config (same pattern
    as embed-client AdapterTransport). call_server and help are kept for
    backward compatibility but chat_flow uses direct_server_client.
    """

    def __init__(self, config: WorkstationConfig) -> None:
        """Initialize with workstation config (proxy URL, token, certs)."""
        self._config = config
        self._adapter_params = config_to_adapter_params(config)
        self._client: Any = None

    def _use_ws_first(self) -> bool:
        """True when proxy URL is wss:// (adapter supports WS; use WS-first)."""
        url = (self._config.mcp_proxy_url or "").strip().lower()
        return url.startswith("wss://")

    async def _get_client(self) -> Any:
        """Lazy-create adapter JsonRpcClient (single instance, mTLS when certs set)."""
        if self._client is not None:
            return self._client
        try:
            from mcp_proxy_adapter.client.jsonrpc_client import JsonRpcClient
        except ImportError as e:
            raise ProxyClientError(
                f"MCP Proxy Adapter client not available: {e}"
            ) from e
        self._client = JsonRpcClient(**self._adapter_params)
        return self._client

    async def _call_ws(
        self, method: str, params: Dict[str, Any], client: Any
    ) -> Dict[str, Any]:
        """
        Run one JSON-RPC request over adapter's bidirectional WS channel.

        Uses open_bidirectional_ws_channel; sends one request, receives one
        response. Raises on connection failure, timeout, or invalid response.
        """
        from mcp_proxy_adapter.client.jsonrpc_client import (
            open_bidirectional_ws_channel,
        )

        req_id = 1
        payload: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": req_id,
        }
        async with open_bidirectional_ws_channel(
            client, receive_timeout=30.0, heartbeat=30.0
        ) as channel:
            await channel.send_json(payload)
            async for msg in channel.receive_iter():
                if not isinstance(msg, dict):
                    continue
                if "result" in msg or "error" in msg:
                    return cast(Dict[str, Any], client._extract_result(msg))
        raise ProxyClientError("WS channel closed without JSON-RPC response")

    async def _call_http(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run JSON-RPC on proxy via adapter HTTP client; return result or raise."""
        client = await self._get_client()
        response = await client.jsonrpc_call(method, params)
        return cast(Dict[str, Any], client._extract_result(response))

    async def _call(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Run JSON-RPC on proxy. WS-first when mcp_proxy_url is wss://; else HTTP.

        Fallback policy: if WS path raises any exception, fall back to HTTP once.
        """
        params = params or {}
        logger.debug(
            "proxy_call start method=%s params_keys=%s", method, list(params.keys())
        )
        try:
            if self._use_ws_first():
                try:
                    client = await self._get_client()
                    return await self._call_ws(method, params, client)
                except Exception as e:  # noqa: BLE001
                    logger.info(
                        "ws_first_fallback method=%s reason=%s using_http",
                        method,
                        type(e).__name__,
                    )
                    return await self._call_http(method, params)
            return await self._call_http(method, params)
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            resp = getattr(e, "response", None)
            status = (
                getattr(e, "status_code", None)
                or getattr(e, "status", None)
                or (getattr(resp, "status_code", None) if resp is not None else None)
            )
            response_body = ""
            if resp is not None and getattr(resp, "text", None):
                response_body = (resp.text or "")[:500]
            logger.warning(
                "proxy_call_failed method=%s status=%s error=%s response_body=%s",
                method,
                status,
                msg,
                response_body or "(none)",
            )
            raise ProxyClientError(msg, status=status) from e

    async def _list_servers_rest(
        self,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        filter_enabled: Optional[bool] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Call proxy GET /list (OpenAPI). Query params: page, page_size, filter_enabled.
        Same mTLS client. Returns None on failure; then use JSON-RPC list_servers.
        """
        client = await self._get_client()
        http = await client._get_client()
        base = client.base_url.rstrip("/")
        query_parts: list[str] = []
        if page is not None:
            query_parts.append(f"page={page}")
        if page_size is not None:
            query_parts.append(f"page_size={page_size}")
        if filter_enabled is not None:
            query_parts.append(f"filter_enabled={str(filter_enabled).lower()}")
        qs = "&".join(query_parts)
        url = f"{base}/list" if not qs else f"{base}/list?{qs}"
        try:
            resp = await http.get(url, headers=client.headers)
            if resp.status_code == 200:
                return cast(Dict[str, Any], resp.json())
        except Exception as e:  # noqa: BLE001
            logger.debug(
                "REST GET /list failed, will try JSON-RPC: %s", e, exc_info=False
            )
        return None

    async def list_servers(
        self,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        filter_enabled: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        List servers via adapter client. Tries REST GET /list (OpenAPI) first,
        then JSON-RPC list_servers. Same client and mTLS for all.
        """
        rest = await self._list_servers_rest(
            page=page, page_size=page_size, filter_enabled=filter_enabled
        )
        if rest is not None:
            return rest
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
