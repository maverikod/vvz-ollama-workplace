#!/usr/bin/env python3
"""
Verify MWPS is running and optionally list models.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import os
import sys

# Optional: use project config default
MWPS_BASE = os.environ.get(
    "MWPS_BASE_URL", "http://127.0.0.1:11434"
)


def main() -> int:
    try:
        import httpx
    except ImportError:
        print("httpx not installed. pip install httpx")
        return 1

    base = MWPS_BASE.rstrip("/")
    print(f"Checking MWPS at {base} ...")

    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.get(f"{base}/api/tags")
            r.raise_for_status()
            data = r.json()
    except httpx.ConnectError as e:
        print(f"Connection failed: {e}")
        print("Start MWPS: mwps serve")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1

    models = data.get("models") or []
    print("OK — MWPS is running.")
    if models:
        print("Models:", ", ".join(m.get("name", "?") for m in models))
    else:
        print("No models yet. Run: mwps pull llama3.2")
    return 0


if __name__ == "__main__":
    sys.exit(main())
