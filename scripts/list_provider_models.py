#!/usr/bin/env python3
"""
Fetch and print available model ids from each provider's API (from config).
Usage: ADAPTER_CONFIG_PATH=<path> python scripts/list_provider_models.py

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


def fetch_models(
    provider: str, base_url: str, api_key: str, timeout: float = 30.0
) -> list[str]:
    """Call provider's list-models endpoint; return list of model ids."""
    base = (base_url or "").strip().rstrip("/")
    key = (api_key or "").strip()
    if not base or not key:
        return []

    if provider == "google":
        # Native endpoint: key as query param
        url = base.replace("/openai/", "").replace("/openai", "").rstrip("/")
        r = httpx.get("%s/models" % url, params={"key": key}, timeout=timeout)
        if r.status_code != 200:
            return []
        data = r.json()
        names = []
        for m in data.get("models") or []:
            name = (m.get("name") or "").strip()
            if name.startswith("models/"):
                name = name[7:]
            if name:
                names.append(name)
        return names

    if provider == "anthropic":
        url = base + "/models"
        headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
        r = httpx.get(url, headers=headers, timeout=timeout)
        if r.status_code != 200:
            return []
        data = r.json()
        return [
            str(m.get("id", "")).strip() for m in data.get("data") or [] if m.get("id")
        ]

    # OpenAI-compatible: GET /v1/models, Bearer token
    url = base + "/models"
    headers = {"Authorization": "Bearer %s" % key}
    r = httpx.get(url, headers=headers, timeout=timeout)
    if r.status_code != 200:
        return []
    data = r.json()
    return [str(m.get("id", "")).strip() for m in data.get("data") or [] if m.get("id")]


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
    mp = ow.get("model_providers") or {}
    if not isinstance(mp, dict):
        print("No model_providers in config", file=sys.stderr)
        return 1

    print("Config: %s" % path, file=sys.stderr)
    print("-" * 60)

    for prov in sorted(mp.keys()):
        if not isinstance(prov, str) or not prov.strip():
            continue
        cfg = mp.get(prov) if isinstance(mp.get(prov), dict) else {}
        url = (cfg.get("url") or "").strip().rstrip("/")
        key = (cfg.get("api_key") or "").strip()
        if prov == "ollama":
            print("[%s] (no list endpoint, use /api/tags for model list)" % prov)
            continue
        if not url or not key:
            print("[%s] skip (no url or api_key)" % prov)
            continue
        try:
            ids = fetch_models(prov, url, key)
            if ids:
                print("[%s] %s" % (prov, ", ".join(ids)))
            else:
                print("[%s] (empty or request failed)" % prov)
        except Exception as e:
            print("[%s] error: %s" % (prov, str(e)[:80]))

    print("-" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
