"""
Thread-safe state for model loading: server reports loading/ready and current.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import threading
from typing import Any, Dict

_lock = threading.Lock()
_is_loading = False
_current_model: str | None = None
_message: str = ""


def set_loading(model: str | None, message: str = "") -> None:
    """Set state to loading; optional current model name and message."""
    with _lock:
        global _is_loading, _current_model, _message
        _is_loading = True
        _current_model = model
        _message = message or (
            f"Loading model {model}..." if model else "Loading..."
        )


def set_ready() -> None:
    """Set state to ready (no model loading)."""
    with _lock:
        global _is_loading, _current_model, _message
        _is_loading = False
        _current_model = None
        _message = ""


def get_state() -> Dict[str, Any]:
    """Return current state dict for API: status, current_model, message."""
    with _lock:
        status = "loading_models" if _is_loading else "ready"
        return {
            "status": status,
            "current_model": _current_model,
            "message": _message
            or (None if not _is_loading else "Loading models..."),
        }
