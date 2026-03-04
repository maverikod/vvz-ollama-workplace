#!/usr/bin/env python3
"""
Read adapter config (JSON) and send a test message to each model; report success/fail.
Uses config path from env ADAPTER_CONFIG_PATH or first existing of:
  config/adapter_config.generated.json, config/adapter_config.json

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import httpx

# Add src to path when run from project root
_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from ollama_workstation.config import load_config  # noqa: E402
from ollama_workstation.model_provider_resolver import (  # noqa: E402
    resolve_model_endpoint,
)
from ollama_workstation.commercial_chat_client import (  # noqa: E402
    chat_completion as commercial_chat,
)

TEST_MESSAGE = "Hi. Reply with one word: OK."
TIMEOUT = 60.0


def _get_config_path() -> Path:
    p = os.environ.get("ADAPTER_CONFIG_PATH")
    if p and Path(p).exists():
        return Path(p)
    for name in (
        "config/adapter_config.json",
        "config/adapter_config.generated.json",
        "config/adapter_config.local.json.example",
    ):
        path = _root / name
        if path.exists():
            return path
    return _root / "config/adapter_config.json"


def _get_model_list(config_path: Path) -> list[str]:
    """Read model list from ollama_workstation.ollama."""
    data = json.loads(config_path.read_text(encoding="utf-8"))
    ow = data.get("ollama_workstation") or {}
    section = ow.get("ollama")
    if not isinstance(section, dict):
        return []
    models = section.get("models") if isinstance(section.get("models"), list) else []
    default = (section.get("model") or "").strip()
    out = [m.strip() for m in models if isinstance(m, str) and m.strip()]
    if not out and default:
        out = [default]
    return out


async def _test_ollama(base_url: str, model: str, timeout: float) -> tuple[bool, str]:
    """Send test message to Ollama /api/chat. Return (ok, message)."""
    url = base_url.rstrip("/") + "/api/chat"
    body = {
        "model": model,
        "messages": [{"role": "user", "content": TEST_MESSAGE}],
        "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(url, json=body)
            if r.status_code != 200:
                return False, "HTTP %s: %s" % (r.status_code, (r.text or "")[:200])
            data = r.json()
            msg = data.get("message") or {}
            content = (msg.get("content") or "").strip()
            return True, content[:80] if content else "(empty)"
    except Exception as e:
        return False, str(e)[:200]


async def _test_commercial(endpoint, timeout: float) -> tuple[bool, str]:
    """Send test message via commercial chat. Return (ok, message)."""
    try:
        data = await commercial_chat(
            endpoint,
            [{"role": "user", "content": TEST_MESSAGE}],
            stream=False,
            timeout=timeout,
        )
        msg = data.get("message") or {}
        content = (msg.get("content") or "").strip()
        return True, content[:80] if content else "(empty)"
    except Exception as e:
        return False, str(e)[:200]


async def _check_model(model: str, config_path: Path) -> tuple[str, bool, str]:
    """Resolve model, send test, return (model, ok, detail)."""
    config = load_config(str(config_path))
    endpoint = resolve_model_endpoint(model, config)
    if endpoint.is_ollama:
        ok, detail = await _test_ollama(endpoint.base_url, endpoint.model_id, TIMEOUT)
    else:
        ok, detail = await _test_commercial(endpoint, TIMEOUT)
    return model, ok, detail


async def main_async(config_path: Path) -> int:
    models = _get_model_list(config_path)
    if not models:
        print(
            "No models in config (ollama_workstation.ollama).",
            file=sys.stderr,
        )
        return 1
    print("Config: %s" % config_path, file=sys.stderr)
    print("Models: %s" % ", ".join(models), file=sys.stderr)
    print("Test message: %s" % TEST_MESSAGE, file=sys.stderr)
    print("-" * 60)

    failed = 0
    for model in models:
        model_id, ok, detail = await _check_model(model, config_path)
        if ok:
            print("[OK] %s -> %s" % (model_id, detail))
        else:
            print("[FAIL] %s -> %s" % (model_id, detail))
            failed += 1
    print("-" * 60)
    print("Passed: %s, Failed: %s" % (len(models) - failed, failed))
    return 1 if failed else 0


def main() -> int:
    config_path = _get_config_path()
    if not config_path.exists():
        print("Config not found: %s" % config_path, file=sys.stderr)
        return 1
    return asyncio.run(main_async(config_path))


if __name__ == "__main__":
    sys.exit(main())
