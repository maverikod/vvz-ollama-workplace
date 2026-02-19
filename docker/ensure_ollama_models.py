#!/usr/bin/env python3
"""
Ensure OLLAMA models from adapter config are present: check which exist,
pull missing ones, and log before/after each pull.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import json
import os
import subprocess
import sys
from pathlib import Path

CONFIG_PATH = os.environ.get(
    "ADAPTER_CONFIG_PATH", "/app/config/adapter_config.json"
)


def _ollama_list_models() -> set[str]:
    """Return set of model names (first column from 'ollama list')."""
    try:
        out = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return set()
    if out.returncode != 0:
        return set()
    names: set[str] = set()
    for line in out.stdout.strip().splitlines()[1:]:  # skip header
        parts = line.split()
        if parts:
            names.add(parts[0])
    return names


def _model_present(list_names: set[str], model: str) -> bool:
    """True if model is in list (exact name or name:tag)."""
    if model in list_names:
        return True
    for name in list_names:
        if name == model or name.startswith(model + ":"):
            return True
    return False


def main() -> int:
    path = Path(CONFIG_PATH)
    if not path.exists():
        print(f"Config not found: {path}", file=sys.stderr)
        return 0  # do not fail startup

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"Failed to read config: {e}", file=sys.stderr)
        return 0

    ow = data.get("ollama_workstation") or {}
    models: list = ow.get("ollama_models") or []
    if not isinstance(models, list):
        return 0
    model_names = [m for m in models if isinstance(m, str) and m.strip()]
    if not model_names:
        return 0

    present = _ollama_list_models()
    for model in model_names:
        if _model_present(present, model):
            continue
        print(f"Loading model {model}...", flush=True)
        try:
            subprocess.run(
                ["ollama", "pull", model],
                check=False,
                timeout=3600,
            )
            print(f"Loaded model {model}.", flush=True)
        except subprocess.TimeoutExpired:
            print(f"Timeout loading model {model}.", file=sys.stderr)
        except Exception as e:
            print(f"Error loading model {model}: {e}", file=sys.stderr)
        else:
            present.add(model)

    return 0


if __name__ == "__main__":
    sys.exit(main())
