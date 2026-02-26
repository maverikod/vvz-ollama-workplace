"""
Thread-safe state for model loading and OLLAMA readiness.

Model ready: set True only after warm_up_models() in run_adapter (models in memory).
Not set by ping: GET /api/tags only means OLLAMA is up; model loads on first /api/chat.

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
# OLLAMA responded to ping; server is "ready" only when this is True. Init False.
_model_ready = False
# Runtime default model for new chats; None = use config.ollama_model. Hot-swappable.
_active_model: str | None = None


def set_model_ready(ready: bool) -> None:
    """Set model readiness (called after warm_up_models in run_adapter)."""
    with _lock:
        global _model_ready
        _model_ready = ready


def is_model_ready() -> bool:
    """Return whether OLLAMA has responded and model is ready for chat."""
    with _lock:
        return _model_ready


def set_loading(model: str | None, message: str = "") -> None:
    """Set state to loading; optional current model name and message."""
    with _lock:
        global _is_loading, _current_model, _message
        _is_loading = True
        _current_model = model
        _message = message or (f"Loading model {model}..." if model else "Loading...")


def set_ready() -> None:
    """Set state to ready (no model loading). Does not set _model_ready."""
    with _lock:
        global _is_loading, _current_model, _message
        _is_loading = False
        _current_model = None
        _message = ""


def get_active_model() -> str | None:
    """Runtime default model (hot-swappable); None = use config.ollama_model."""
    with _lock:
        return _active_model


def set_active_model(model: str | None) -> None:
    """Set runtime default model for new chats. None = reset to config."""
    with _lock:
        global _active_model
        _active_model = model.strip() if (model and model.strip()) else None


def get_state() -> Dict[str, Any]:
    """State for API: status, current_model, message, active_model."""
    with _lock:
        msg: str | None
        if _is_loading:
            status = "loading_models"
            msg = _message or "Loading models..."
        elif not _model_ready:
            status = "loading_models"
            msg = "Waiting for OLLAMA..."
        else:
            status = "ready"
            msg = _message or None
        return {
            "status": status,
            "current_model": _current_model,
            "message": msg,
            "active_model": _active_model,
        }
