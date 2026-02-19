"""
Run model loading from config in background; updates model_loading_state.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .model_loading_state import set_loading, set_ready


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
    for line in (out.stdout or "").strip().splitlines()[1:]:
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


def run_model_loading(config_path: str) -> None:
    """
    Read model list from config, pull missing models, update loading state.
    Call from a background thread; sets ready() when done.
    """
    set_ready()
    path = Path(config_path)
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    ow = data.get("ollama_workstation") or {}
    models: list = ow.get("ollama_models") or []
    if not isinstance(models, list):
        return
    model_names = [m for m in models if isinstance(m, str) and m.strip()]
    if not model_names and ow.get("ollama_model"):
        default = str(ow.get("ollama_model", "")).strip()
        if default:
            model_names = [default]
    if not model_names:
        return
    present = _ollama_list_models()
    for model in model_names:
        if _model_present(present, model):
            continue
        set_loading(model, f"Loading model {model}...")
        try:
            subprocess.run(
                ["ollama", "pull", model],
                check=False,
                timeout=3600,
            )
            present.add(model)
        except subprocess.TimeoutExpired:
            set_loading(model, f"Timeout loading model {model}.")
        except Exception as e:
            set_loading(model, f"Error: {e}")
    set_ready()
