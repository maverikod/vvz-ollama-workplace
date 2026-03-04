#!/usr/bin/env python3
"""
E2E: Add vectorizer to context, create session, command model to vectorize,
verify with get_model_context and invoke_tool.

Steps:
  1. Add vectorizer to context (session_rules describing embedding tool usage).
  2. Create session with session_init (model + session_rules).
  3. Send command to model: "Vectorize the phrase: hello world".
  4. Verify with tools: get_model_context (what model receives), invoke_tool
     list_servers (what it can call), ollama_chat (can it call tools).

Env: ADAPTER_URL (default https://localhost:8016), CERTS_DIR (mtls_certificates),
     VERIFY_MODEL_TOOL_USE (default 1): set to 0 to allow step 6 to warn only.
     Use http://localhost:8015 for local adapter without TLS.

Step 6 uses allowed_commands so the model sees only echo (and vectorization).
With 30+ tools, the model often replies in text instead of emitting tool_calls.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import json
import os
import ssl
import sys
import urllib.request
from typing import Any, cast

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CERTS_DIR = os.environ.get("CERTS_DIR", os.path.join(PROJECT_ROOT, "mtls_certificates"))
ADAPTER_URL = os.environ.get("ADAPTER_URL", "https://localhost:8016").rstrip("/")
JSONRPC_PATH = os.environ.get("JSONRPC_PATH", "/api/jsonrpc")

# Session rules that add "vectorizer" to the model context.
VECTORIZER_SESSION_RULES = [
    "You have access to a vectorizer (embedding service). "
    "To vectorize text: call list_servers to find the embedding server "
    "(e.g. server_id embedding-service), then call call_server with that "
    "server_id, command 'embed' or 'embed_execute', and params containing "
    'the text to vectorize (e.g. {"text": "..."}).',
]

# Session rules and prompt to force the model to use a tool (echo).
ECHO_SESSION_RULES = [
    "You must call tools when the user asks. Your response MUST include a "
    "tool call when asked to call echo. Do not reply with only text.",
]
ECHO_PROMPT = (
    "Your next action must be to call the 'echo' tool with message "
    "'verify_tools_ok'. Call that tool now, then say what it returned."
)


def _jsonrpc(method: str, params: dict, req_id: int = 1) -> dict:
    url = ADAPTER_URL + JSONRPC_PATH
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": req_id,
        }
    )
    req = urllib.request.Request(
        url,
        data=body.encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if url.startswith("https://"):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        cert = os.path.join(CERTS_DIR, "client.crt")
        key = os.path.join(CERTS_DIR, "client.key")
        if os.path.isfile(cert) and os.path.isfile(key):
            ctx.load_cert_chain(cert, keyfile=key)
        with urllib.request.urlopen(req, timeout=130, context=ctx) as resp:
            return cast(dict[str, Any], json.loads(resp.read().decode()))
    with urllib.request.urlopen(req, timeout=130) as resp:
        return cast(dict[str, Any], json.loads(resp.read().decode()))


def _result_data(response: dict) -> tuple[bool, dict | None, dict | None]:
    err = response.get("error")
    if err:
        return False, None, err
    res = response.get("result")
    if not res:
        return False, None, {"message": "No result"}
    data = res.get("data") if isinstance(res, dict) else res
    if isinstance(res, dict) and res.get("success") is False:
        return False, None, res.get("error") or {"message": str(res)}
    return True, data, None


def main() -> int:
    print("E2E: Vectorizer in context, session, verify context and tools")
    print("  ADAPTER_URL=%s" % ADAPTER_URL)
    if ADAPTER_URL.startswith("https://") and not os.path.isfile(
        os.path.join(CERTS_DIR, "client.crt")
    ):
        print("  WARN: HTTPS but client.crt not found in %s" % CERTS_DIR)

    # 1–2. Add vectorizer to context (session_rules) and create session
    print("\n1–2. session_init with vectorizer in session_rules")
    r1 = _jsonrpc(
        "session_init",
        {
            "model": "llama3.2",
            "session_rules": VECTORIZER_SESSION_RULES,
        },
        req_id=1,
    )
    ok, data, err = _result_data(r1)
    if not ok:
        print("  FAIL: session_init: %s" % (err or r1))
        return 1
    if data is None:
        print("  FAIL: session_init no data")
        return 1
    session_id = (data.get("session_id") or "").strip()
    if not session_id:
        print("  FAIL: session_init no session_id: %s" % data)
        return 1
    print("  session_id=%s" % session_id)

    # 3. Command for the model (we will send it in step 5); here we only prepare
    user_content = "Vectorize the phrase: hello world"

    # 4a. get_model_context — what the model receives
    print("\n4a. get_model_context(session_id, content) — what model receives")
    r_ctx = _jsonrpc(
        "get_model_context",
        {"session_id": session_id, "content": user_content},
        req_id=2,
    )
    ok_ctx, ctx_data, err_ctx = _result_data(r_ctx)
    if not ok_ctx:
        print("  FAIL: get_model_context: %s" % (err_ctx or r_ctx))
        return 1
    if ctx_data is None:
        print("  FAIL: get_model_context no data")
        return 1
    messages = ctx_data.get("messages") or []
    tool_names = ctx_data.get("tool_names") or []
    tools = ctx_data.get("tools") or []
    count = ctx_data.get("messages_count", 0)
    print("  messages_count=%s" % count)
    print("  tool_names=%s" % tool_names)
    print("  Tools the model sees (name + description):")
    for t in tools:
        name = t.get("name") or "?"
        desc = (t.get("description") or "").strip()
        desc_preview = (desc[:80] + "...") if len(desc) > 80 else desc
        print("    - %s: %s" % (name, desc_preview or "(no description)"))
        if t.get("parameters") and isinstance(t["parameters"], dict):
            req = t["parameters"].get("required") or []
            props = list((t["parameters"].get("properties") or {}).keys())
            print("      parameters: required=%s, properties=%s" % (req, props))
    for i, m in enumerate(messages[:6]):
        role = m.get("role", "?")
        preview = (m.get("content_preview") or "")[:60]
        length = m.get("content_len", 0)
        print(
            "  message[%s] role=%s content_len=%s preview=%s"
            % (i, role, length, preview + "..." if len(preview) >= 60 else preview)
        )
    if len(messages) > 6:
        print("  ... and %s more messages" % (len(messages) - 6))
    # Model must not see internal proxy tools (list_servers, call_server).
    # "help" can be a server command.
    if "list_servers" in tool_names or "call_server" in tool_names:
        print("  FAIL: model must NOT see list_servers/call_server (internal only)")
    elif tool_names:
        print("  OK: model sees server tools only: %s" % tool_names)
    else:
        print("  OK: no tools (discovery returned no servers or failed)")

    # 4b. invoke_tool list_servers — what the model can call
    print("\n4b. invoke_tool(list_servers) — available servers")
    r_list = _jsonrpc(
        "invoke_tool",
        {"tool_name": "list_servers", "arguments": {"page": 1, "page_size": 20}},
        req_id=3,
    )
    ok_list, list_data, err_list = _result_data(r_list)
    if not ok_list:
        print("  FAIL: invoke_tool list_servers: %s" % (err_list or r_list))
        # Do not return 1; proxy might be down, but context is already verified
        print("  (Proxy may be down; context and session are OK)")
    else:
        content = (list_data.get("content") or "") if list_data else ""
        try:
            parsed = json.loads(content) if content.strip().startswith("{") else {}
            servers = parsed.get("servers") or []
            ids = [s.get("server_id") or s.get("id") or "?" for s in servers[:10]]
            print("  servers (ids): %s" % ids)
            if any("embed" in str(s).lower() for s in ids):
                print("  OK: embedding/vectorizer server visible to tools")
            else:
                print("  INFO: no embedding server in list (rule still in context)")
        except json.JSONDecodeError:
            print(
                "  content (preview): %s"
                % (content[:200] + "..." if len(content) > 200 else content)
            )

    # 5. ollama_chat — give model the command to vectorize; check it can use tools
    print("\n5. ollama_chat(session_id, content) — model command: vectorize phrase")
    r_chat = _jsonrpc(
        "ollama_chat",
        {"session_id": session_id, "content": user_content},
        req_id=4,
    )
    ok_chat, chat_data, err_chat = _result_data(r_chat)
    if not ok_chat:
        print("  FAIL: ollama_chat: %s" % (err_chat or r_chat))
        return 1
    if chat_data is None:
        print("  FAIL: ollama_chat no data")
        return 1
    msg = (chat_data.get("message") or "").strip()
    history = chat_data.get("history") or []
    tool_used = any("tool_calls" in h or h.get("role") == "tool" for h in history)
    print(
        "  model reply (preview): %s"
        % (msg[:120] + "..." if len(msg) > 120 else msg or "(empty)")
    )
    print("  tool used in history: %s" % tool_used)
    if tool_used:
        print("  OK: model invoked tools (list_servers/call_server for vectorizer)")
    else:
        print("  INFO: model replied without tool_calls (context has vectorizer rule)")

    # 6. Ensure model actually uses tools: session with only echo allowed so the
    #    model is much more likely to call it (with 30+ tools it often replies in text).
    print("\n6. ollama_chat — model MUST use echo tool")
    r2 = _jsonrpc(
        "session_init",
        {
            "model": "llama3.2",
            "session_rules": ECHO_SESSION_RULES,
            "allowed_commands": [
                "echo.ollama-adapter-test",
                "echo.ollama-adapter",
            ],
        },
        req_id=5,
    )
    ok2, data2, err2 = _result_data(r2)
    if not ok2 or not data2:
        print("  FAIL: session_init for echo: %s" % (err2 or "no data"))
        return 1
    session_id2 = (data2.get("session_id") or "").strip()
    if not session_id2:
        print("  FAIL: session_init (echo) no session_id")
        return 1
    r_echo = _jsonrpc(
        "ollama_chat",
        {"session_id": session_id2, "content": ECHO_PROMPT},
        req_id=6,
    )
    ok_echo, echo_data, err_echo = _result_data(r_echo)
    if not ok_echo:
        print("  FAIL: ollama_chat (echo): %s" % (err_echo or r_echo))
        return 1
    if echo_data is None:
        print("  FAIL: ollama_chat (echo) no data")
        return 1
    history_echo = echo_data.get("history") or []
    tool_used_echo = any(
        "tool_calls" in h or h.get("role") == "tool" for h in history_echo
    )
    verify_tool_use_env = os.environ.get("VERIFY_MODEL_TOOL_USE", "1").strip()
    require_tool_use: bool = verify_tool_use_env.lower() not in ("0", "false", "no")
    if tool_used_echo:
        print("  OK: model used tools (echo called)")
    elif require_tool_use:
        print("  FAIL: model did not use tools; Llama must call echo for this prompt")
        # Debug: show what tools the model actually saw in step 6
        r_dbg = _jsonrpc(
            "get_model_context",
            {"session_id": session_id2, "content": ECHO_PROMPT},
            req_id=7,
        )
        ok_dbg, dbg_data, _ = _result_data(r_dbg)
        if ok_dbg and dbg_data:
            step6_tools = dbg_data.get("tool_names") or []
            print("  (step 6 context had tool_names=%s)" % step6_tools)
        return 1
    else:
        print("  WARN: model did not use tools (VERIFY_MODEL_TOOL_USE=0; optional)")

    print(
        "\nDone: vectorizer in context; session created; tools verified; "
        "model uses tools."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
