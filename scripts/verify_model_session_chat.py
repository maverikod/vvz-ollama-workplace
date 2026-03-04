#!/usr/bin/env python3
"""
E2E: session_init -> ollama_chat(session_id, content) against real adapter; model runs.
Requires: container with new adapter (session_id/content) + OLLAMA, client certs.
Env: ADAPTER_URL (default https://localhost:8016), CERTS_DIR (mtls_certificates),
VERIFY_CLIENT_TIMEOUT (default 180). Adapter: command_execution_timeout_seconds (120),
ollama_timeout (60 in config; increase for slow/cold model).
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
import ssl

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CERTS_DIR = os.environ.get("CERTS_DIR", os.path.join(PROJECT_ROOT, "mtls_certificates"))
ADAPTER_URL = os.environ.get("ADAPTER_URL", "https://localhost:8016").rstrip("/")
JSONRPC_PATH = os.environ.get("JSONRPC_PATH", "/api/jsonrpc")
CLIENT_TIMEOUT = int(os.environ.get("VERIFY_CLIENT_TIMEOUT", "180"))


def _jsonrpc(method: str, params: dict, id: int = 1) -> dict:
    url = ADAPTER_URL + JSONRPC_PATH
    body = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": id})
    req = urllib.request.Request(
        url,
        data=body.encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.load_cert_chain(
        os.path.join(CERTS_DIR, "client.crt"),
        keyfile=os.path.join(CERTS_DIR, "client.key"),
    )
    with urllib.request.urlopen(req, timeout=CLIENT_TIMEOUT, context=ctx) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    print("E2E: session_init -> ollama_chat(session_id, content) with real model")
    print("  ADAPTER_URL=%s client_timeout=%ss" % (ADAPTER_URL, CLIENT_TIMEOUT))
    if not os.path.isfile(os.path.join(CERTS_DIR, "client.crt")):
        print("  SKIP: client.crt not found in %s" % CERTS_DIR)
        return 0

    try:
        r1 = _jsonrpc("session_init", {}, id=1)
    except Exception as e:
        print("  FAIL: session_init: %s" % e)
        return 1
    res = r1.get("result")
    if not res:
        print("  FAIL: session_init no result: %s" % r1)
        return 1
    data = res.get("data") if isinstance(res, dict) else None
    if not data:
        data = res
    session_id = (data.get("session_id") or "").strip()
    if not session_id:
        print("  FAIL: session_init no session_id: %s" % r1)
        return 1
    print("  session_id=%s" % session_id)

    try:
        r2 = _jsonrpc(
            "ollama_chat",
            {"session_id": session_id, "content": "Reply with exactly: OK"},
            id=2,
        )
    except Exception as e:
        err_str = str(e).lower()
        if "timeout" in err_str or "timed out" in err_str:
            print(
                "  FAIL: ollama_chat timeout (increase VERIFY_CLIENT_TIMEOUT and/or "
                "ollama_timeout in adapter config). %s" % e
            )
        else:
            print("  FAIL: ollama_chat: %s" % e)
        return 1
    err = r2.get("error")
    if err:
        print("  FAIL: ollama_chat error: %s" % err)
        return 1
    res2 = r2.get("result")
    if not res2:
        print("  FAIL: ollama_chat no result: %s" % r2)
        return 1
    data2 = res2.get("data") if isinstance(res2, dict) else res2
    if isinstance(res2, dict) and res2.get("success") is False:
        err = res2.get("error") or {}
        print("  FAIL: ollama_chat error: %s" % err.get("message", res2))
        print(
            "  (Adapter may be old build without session_id/content; use test container.)"
        )
        return 1
    msg = (data2.get("message") or "").strip() if data2 else ""
    if not msg:
        print("  FAIL: ollama_chat returned empty message.")
        print("  Full response (for diagnosis): %s" % json.dumps(r2)[:800])
        print(
            "  Tips: (1) Timeout: increase ollama_timeout in adapter config (e.g. 120) "
            "and VERIFY_CLIENT_TIMEOUT (e.g. 300)."
        )
        print(
            "  (2) Empty from model: check container logs for '500' on POST /api/chat "
            "(OLLAMA error) or 'model_reply content_len=0' (OLLAMA returned empty)."
        )
        return 1
    print("  model reply: %s" % (msg[:80] + "..." if len(msg) > 80 else msg))
    print("  OK: model ran and returned a reply")
    return 0


if __name__ == "__main__":
    sys.exit(main())
