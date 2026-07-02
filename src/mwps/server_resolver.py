"""
Resolve server_id to server_url and connection params from proxy list_servers.

Addresses, ports, protocols are obtained from the proxy list; used for direct
connections (embed-client, svo-client) instead of proxy call_server.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from .config import WorkstationConfig

logger = logging.getLogger(__name__)


def extract_servers_list(raw: Dict[str, Any]) -> list:
    """
    Extract list of server dicts from list_servers response.

    Handles flat {servers: [...]} and nested {data: {servers: [...]}} or
    {result: {servers: [...]}} (e.g. OpenAPI GET /list, JSON-RPC).
    Returns empty list if structure is unknown.
    """
    servers = raw.get("servers") or raw.get("items")
    if servers is None and isinstance(raw.get("data"), dict):
        servers = raw["data"].get("servers") or raw["data"].get("items")
    if servers is None and isinstance(raw.get("result"), dict):
        servers = raw["result"].get("servers") or raw["result"].get("items")
    return servers if isinstance(servers, list) else []


def _server_url_cache_from_list_servers(raw: Dict[str, Any]) -> Dict[str, str]:
    """Build server_id -> server_url from list_servers response."""
    out: Dict[str, str] = {}
    servers = extract_servers_list(raw)
    for srv in servers:
        if not isinstance(srv, dict):
            continue
        sid = (srv.get("server_id") or srv.get("id") or "").strip()
        url = (srv.get("server_url") or srv.get("url") or "").strip()
        if sid and url:
            out[sid] = url
    return out


async def get_server_url(
    list_servers_fn: Any,
    server_id: str,
) -> Optional[str]:
    """
    Resolve server_id to server_url using proxy list_servers.

    Args:
        list_servers_fn: Async callable that returns list_servers result
            (e.g. proxy.list_servers).
        server_id: Server identifier (e.g. embedding-service, svo-chunker).

    Returns:
        server_url (e.g. https://embedding-service:8008) or None if not found.
    """
    if not (server_id or "").strip():
        return None
    try:
        raw = await list_servers_fn()
        cache = _server_url_cache_from_list_servers(raw)
        return cache.get(server_id.strip())
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "get_server_url list_servers failed server_id=%s: %s",
            server_id,
            e,
        )
        return None


def parse_server_url(server_url: str) -> Dict[str, Any]:
    """
    Parse server_url to protocol, host, port for adapter/client use.

    Returns:
        dict with protocol ("http"|"https"), host (str), port (int).
        Port defaults to 443 for https, 80 for http if missing in URL.
    """
    url = (server_url or "").strip()
    if not url:
        return {"protocol": "http", "host": "localhost", "port": 80}
    parsed = urlparse(url if "://" in url else "http://" + url)
    scheme = (parsed.scheme or "http").lower()
    host = parsed.hostname or "localhost"
    port = parsed.port
    if port is None:
        port = 443 if scheme == "https" else 80
    protocol = "https" if scheme == "https" else "http"
    return {"protocol": protocol, "host": host, "port": port}


def server_url_to_embed_config_dict(
    server_url: str,
    config: "WorkstationConfig",
) -> Dict[str, Any]:
    """
    Build embed-client config_dict from server_url and workstation config.

    Uses proxy_client_cert, proxy_client_key, proxy_ca_cert from config for
    mTLS when server_url is https. Adapter (embed-client) connects directly
    to the service at server_url.
    """
    parsed = parse_server_url(server_url)
    ssl_enabled = parsed["protocol"] == "https"
    cert = getattr(config, "proxy_client_cert", None)
    key = getattr(config, "proxy_client_key", None)
    ca = getattr(config, "proxy_ca_cert", None)
    return {
        "server": {
            "base_url": server_url.rstrip("/"),
            "host": parsed["host"],
            "port": parsed["port"],
        },
        "ssl": {
            "enabled": ssl_enabled,
            "cert_file": cert if (cert and key) else None,
            "key_file": key if (cert and key) else None,
            "ca_cert_file": ca,
            "check_hostname": False,
        },
        "client": {"timeout": 60.0},
    }
