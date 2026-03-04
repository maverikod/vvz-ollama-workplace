"""
Shared OLLAMA HTTP client (keep-alive) and readiness ping thread.

All chat messages to OLLAMA are sent through a single long-lived connection
when possible: get_ollama_client() returns one AsyncClient per process,
reused for every /api/chat request (connection keep-alive).

Readiness: ping thread checks OLLAMA reachable; model_ready set after warm_up.
First connection (ping) uses PING_TIMEOUT_SEC (e.g. 5 min).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Timeout for first connection (ping GET /api/tags). 5 minutes.
PING_TIMEOUT_SEC = 300.0

_client: Optional[httpx.AsyncClient] = None
_client_lock = threading.Lock()
_client_base_url: Optional[str] = None
_client_timeout: Optional[float] = None


def get_ollama_client(base_url: str, timeout: float) -> httpx.AsyncClient:
    """
    Return a long-lived async client for OLLAMA (connection keep-alive).
    Creates once and reuses so all messages go through one connection when possible.
    Same base_url/timeout assumed after first call.
    """
    global _client, _client_base_url, _client_timeout
    with _client_lock:
        if _client is None:
            _client_base_url = (base_url or "").rstrip("/")
            _client_timeout = timeout
            _client = httpx.AsyncClient(timeout=timeout)
            logger.info(
                "ollama_client created base_url=%s timeout=%s",
                _client_base_url,
                _client_timeout,
            )
        return _client


def _readiness_ping_worker(base_url: str) -> None:
    """
    Run in background thread: one GET /api/tags to check OLLAMA is reachable.
    Does NOT set model_ready: ready is set only after warm_up_models() in run_adapter.
    First connection timeout: PING_TIMEOUT_SEC (5 min).
    """
    url = (base_url or "").rstrip("/") + "/api/tags"
    t0 = time.perf_counter()
    try:
        with httpx.Client(timeout=PING_TIMEOUT_SEC) as client:
            resp = client.get(url)
            duration = time.perf_counter() - t0
            if resp.status_code == 200:
                logger.info(
                    "ollama_client ping OK duration_sec=%.2f",
                    duration,
                )
            else:
                logger.warning(
                    "ollama_client ping non-200 after %.2fs: %s status=%s",
                    duration,
                    url,
                    resp.status_code,
                )
    except Exception as e:
        logger.warning(
            "ollama_client ping failed after %.2fs: %s",
            time.perf_counter() - t0,
            e,
        )


def start_readiness_ping_thread(base_url: str) -> None:
    """
    Start a daemon thread that pings OLLAMA once (timeout PING_TIMEOUT_SEC).
    Does not set model_ready; ready is set after warm_up_models in run_adapter.
    """
    if not (base_url or "").strip():
        return
    t = threading.Thread(
        target=_readiness_ping_worker,
        args=((base_url or "").strip(),),
        daemon=True,
        name="ollama-readiness-ping",
    )
    t.start()
    logger.info("ollama_client readiness ping thread started base_url=%s", base_url)
