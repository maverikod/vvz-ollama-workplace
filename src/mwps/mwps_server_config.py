"""
Resolve Model Workplace Server base URL and timeout from adapter config for mwps-server commands.

Used when adapter runs with registration.server_id=mwps-server. Reads from
mwps_server.base_url or mwps.mwps.base_url.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

_DEFAULT_BASE_URL = "http://127.0.0.1:11434"
_DEFAULT_TIMEOUT = 60.0


def get_mwps_server_settings(config_data: Any) -> Tuple[str, float]:
    """
    Get base_url and timeout for Model Workplace Server API from adapter config.

    Prefers mwps_server.base_url / request_timeout_seconds; falls back to
    mwps.mwps.base_url and timeout (or 120).

    Args:
        config_data: Adapter config dict (e.g. get_config().config_data).

    Returns:
        (base_url, timeout_seconds). base_url has no trailing slash.
    """
    if not isinstance(config_data, dict):
        return (_DEFAULT_BASE_URL, _DEFAULT_TIMEOUT)

    # mwps_server section (dedicated for mwps-server adapter)
    oss: Dict[str, Any] = config_data.get("mwps_server") or {}
    if isinstance(oss, dict):
        base = (oss.get("base_url") or "").strip().rstrip("/")
        if base:
            timeout_val = oss.get("request_timeout_seconds")
            if isinstance(timeout_val, (int, float)) and timeout_val > 0:
                return (base, float(timeout_val))
            return (base, _DEFAULT_TIMEOUT)

    # mwps.mwps (shared config shape)
    ow: Dict[str, Any] = config_data.get("mwps") or {}
    if isinstance(ow, dict):
        oo: Dict[str, Any] = ow.get("mwps") or {}
        if isinstance(oo, dict):
            base = (
                (oo.get("base_url") or oo.get("model_server_url") or "")
                .strip()
                .rstrip("/")
            )
            if base:
                timeout_val = oo.get("timeout")
                if isinstance(timeout_val, (int, float)) and timeout_val > 0:
                    return (base, float(timeout_val))
                return (base, _DEFAULT_TIMEOUT)

    return (_DEFAULT_BASE_URL, _DEFAULT_TIMEOUT)
