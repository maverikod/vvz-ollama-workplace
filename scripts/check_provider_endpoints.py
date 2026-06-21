#!/usr/bin/env python3
"""
Read config JSON, for each model get url+key from model_providers by provider name,
send one request to that URL. No resolver, no load_config.
On local Ollama 500 (e.g. CUDA OOM), logs a message; does not start or restart Ollama.

Usage: ADAPTER_CONFIG_PATH=<path> python scripts/check_provider_endpoints.py

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import json
import os
import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    print("pip install httpx", file=sys.stderr)
    sys.exit(1)

# model_id prefix -> provider (same as docker_config_validation)
MODEL_TO_PROVIDER = [
    ("gemini", "google"),
    ("claude", "anthropic"),
    ("gpt-4", "openai"),
    ("gpt-3.5", "openai"),
    ("gpt-35", "openai"),
    ("o1-", "openai"),
    ("grok", "xai"),
    ("deepseek", "deepseek"),
]


def provider_for_model(model_id: str) -> str:
    if not model_id:
        return "ollama"
    m = model_id.strip().lower()
    for prefix, prov in MODEL_TO_PROVIDER:
        if m.startswith(prefix):
            return prov
    return "ollama"


def _is_local_ollama(url: str) -> bool:
    u = (url or "").strip().lower().replace("https://", "").replace("http://", "")
    return u.startswith("127.0.0.1") or u.startswith("localhost")


def main() -> int:
    config_path = os.environ.get(
        "ADAPTER_CONFIG_PATH", "config/adapter_config.generated.json"
    )
    path = Path(config_path)
    if not path.exists():
        print("Config not found: %s" % path, file=sys.stderr)
        return 1

    data = json.loads(path.read_text(encoding="utf-8"))
    ow = data.get("ollama_workstation") or {}
    ollama = ow.get("ollama")
    if not isinstance(ollama, dict):
        print("ollama_workstation.ollama not found", file=sys.stderr)
        return 1
    models = ollama.get("models") or []
    if not models and ollama.get("model"):
        models = [ollama.get("model")]
    mp = ow.get("model_providers") or {}
    timeout = 60.0
    msg = "Hi. Reply with one word: OK."

    print("Config: %s" % path, file=sys.stderr)
    print("Models: %s" % ", ".join(models), file=sys.stderr)
    print("-" * 60)

    failed = 0
    for model in models:
        if not isinstance(model, str) or not model.strip():
            continue
        model = model.strip()
        prov = provider_for_model(model)
        prov_cfg = mp.get(prov) if isinstance(mp, dict) else {}
        url = (prov_cfg.get("url") or "").strip().rstrip("/")
        key = (prov_cfg.get("api_key") or "").strip()

        if not url:
            print("[FAIL] %s -> no url for provider %s" % (model, prov))
            failed += 1
            continue
        if prov != "ollama" and not key:
            print("[FAIL] %s -> no api_key for provider %s" % (model, prov))
            failed += 1
            continue

        if prov == "ollama":
            chat_url = url + "/api/chat"
            body = {
                "model": model,
                "messages": [{"role": "user", "content": msg}],
                "stream": False,
                "options": {"num_gpu": 0},  # force CPU to avoid CUDA OOM
            }
            headers = {"Content-Type": "application/json"}
        else:
            chat_url = url + "/chat/completions"
            body = {
                "model": model,
                "messages": [{"role": "user", "content": msg}],
                "stream": False,
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer %s" % key,
            }

        try:
            r = httpx.post(chat_url, json=body, headers=headers, timeout=timeout)
            if prov == "ollama" and r.status_code == 500:
                err_snippet = (r.text or "")[:200]
                if _is_local_ollama(url) and (
                    "cuda" in err_snippet.lower()
                    or "out of memory" in err_snippet.lower()
                ):
                    print(
                        "  [Ollama] Local Ollama returned 500 (CUDA/OOM). "
                        "Use ollama-adapter container or run Ollama in CPU mode.",
                        file=sys.stderr,
                    )
            if r.status_code == 200:
                out = r.json()
                if prov == "ollama":
                    content = (out.get("message") or {}).get("content") or ""
                else:
                    content = (out.get("choices") or [{}])[0].get("message", {}).get(
                        "content"
                    ) or ""
                print(
                    "[OK] %s -> %s (POST %s)"
                    % (model, (content or "(empty)")[:60], url)
                )
            else:
                err_snippet = (r.text or "")[:200]
                print(
                    "[FAIL] %s -> HTTP %s %s"
                    % (model, r.status_code, err_snippet[:120])
                )
                failed += 1
        except Exception as e:
            print("[FAIL] %s -> %s" % (model, str(e)[:120]))
            failed += 1

    print("-" * 60)
    print("Passed: %s, Failed: %s" % (len(models) - failed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
