"""
Run model loading from config; pull via API, warm up so first chat is not cold.
Uses model server HTTP API (GET /api/tags, POST /api/pull). No subprocess ollama CLI.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import List, Set

from .model_loading_state import set_loading, set_ready

logger = logging.getLogger(__name__)


def _ollama_list_models_via_api(base_url: str, timeout_sec: float = 30.0) -> Set[str]:
    """Return set of model names from GET /api/tags."""
    names: Set[str] = set()
    try:
        import httpx
    except ImportError:
        return names
    base = (base_url or "").rstrip("/")
    if not base:
        return names
    try:
        with httpx.Client(timeout=timeout_sec) as client:
            r = client.get("%s/api/tags" % base)
            if r.status_code != 200:
                return names
            data = r.json()
            for item in data.get("models") or []:
                if isinstance(item, dict):
                    n = item.get("name") or item.get("model")
                    if isinstance(n, str) and n.strip():
                        names.add(n.strip())
    except Exception as e:
        logger.warning("_ollama_list_models_via_api failed: %s", e)
    return names


def _model_present(list_names: Set[str], model: str) -> bool:
    """True if model is in list (exact name or name:tag)."""
    if model in list_names:
        return True
    for name in list_names:
        if name == model or name.startswith(model + ":"):
            return True
    return False


def _ollama_pull_via_api(
    base_url: str, model: str, timeout_sec: float = 3600.0
) -> bool:
    """POST /api/pull for model. Returns True on success."""
    try:
        import httpx
    except ImportError:
        return False
    base = (base_url or "").rstrip("/")
    if not base or not (model or "").strip():
        return False
    try:
        with httpx.Client(timeout=timeout_sec) as client:
            r = client.post(
                "%s/api/pull" % base,
                json={"model": model, "stream": False},
            )
            return r.status_code == 200
    except Exception as e:
        logger.warning("_ollama_pull_via_api %s failed: %s", model, e)
        return False


def run_model_loading_via_api(
    base_url: str,
    model_names: List[str],
    pull_timeout_sec: float = 3600.0,
) -> None:
    """
    Pull missing models via model server API; update loading state.
    Uses GET /api/tags and POST /api/pull. Call from background thread.
    """
    if not (base_url or "").strip():
        return
    set_ready()
    if not model_names:
        return
    t0 = time.perf_counter()
    present = _ollama_list_models_via_api(base_url)
    pulled = 0
    logger.info("Model loading via API: checking/pulling %s models", len(model_names))
    for model in model_names:
        if not (model and str(model).strip()):
            continue
        if _model_present(present, model):
            continue
        set_loading(model, f"Loading model {model}...")
        t_pull = time.perf_counter()
        if _ollama_pull_via_api(base_url, model, timeout_sec=pull_timeout_sec):
            present.add(model)
            pulled += 1
            logger.info(
                "run_model_loading_via_api pull %s duration_sec=%.2f",
                model,
                time.perf_counter() - t_pull,
            )
        else:
            logger.warning("run_model_loading_via_api pull %s failed", model)
    set_ready()
    logger.info(
        "run_model_loading_via_api done duration_sec=%.2f pulled=%s",
        time.perf_counter() - t0,
        pulled,
    )


def run_model_loading(config_path: str) -> None:
    """
    Read model list and model_server_url from config; ensure container if configured,
    then pull missing models via API and set loading state.
    Call from a background thread; uses API only (no ollama CLI).
    """
    set_ready()
    path = Path(config_path)
    if not path.exists():
        return
    t0 = time.perf_counter()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    ow = data.get("ollama_workstation") or {}
    section = ow.get("ollama")
    if not isinstance(section, dict):
        return
    base_url = (
        section.get("model_server_url") or section.get("base_url") or ""
    ).strip()
    models = section.get("models") if isinstance(section.get("models"), list) else []
    default_model = (section.get("model") or "").strip()
    container_name = (section.get("container_name") or "").strip()
    image = (section.get("container_image") or "").strip()
    if not base_url:
        return
    if not isinstance(models, list):
        return
    model_names = [m for m in models if isinstance(m, str) and m.strip()]
    if not model_names and default_model:
        model_names = [default_model]
    if not model_names:
        return
    if container_name and image:
        from .model_server_container import ensure_model_server_container

        if not ensure_model_server_container(container_name, image):
            logger.warning("Model server container not ready; continuing with API")
    run_model_loading_via_api(base_url, model_names, pull_timeout_sec=3600.0)
    logger.info("run_model_loading done duration_sec=%.2f", time.perf_counter() - t0)


def warm_up_models(
    ollama_base_url: str,
    model_names: List[str],
    timeout_sec: float = 120.0,
) -> None:
    """
    Send a minimal chat request per model so OLLAMA loads it into memory.
    Run before starting the adapter server so the first ollama_chat is not cold.
    """
    if not model_names or not (ollama_base_url or "").strip():
        return
    base = (ollama_base_url or "").rstrip("/")
    try:
        import httpx
    except ImportError:
        logger.warning("httpx not available; skipping model warm-up")
        return
    payload = {
        "model": "",
        "messages": [{"role": "user", "content": "Hi"}],
        "stream": False,
    }
    t0 = time.perf_counter()
    for model in model_names:
        if not (model and str(model).strip()):
            continue
        set_loading(model, f"Warming up model {model}...")
        logger.info("Model loading: warming up %s (server remains responsive)", model)
        payload["model"] = model
        t_model = time.perf_counter()
        try:
            with httpx.Client(timeout=timeout_sec) as client:
                r = client.post(
                    f"{base}/api/chat",
                    json=payload,
                )
                duration = time.perf_counter() - t_model
                if r.status_code == 200:
                    logger.info(
                        "warm_up_models %s duration_sec=%.2f",
                        model,
                        duration,
                    )
                else:
                    logger.warning(
                        "Warm-up model %s returned %s (%.2fs): %s",
                        model,
                        r.status_code,
                        duration,
                        (r.text or "")[:200],
                    )
        except Exception as e:
            logger.warning(
                "Warm-up model %s failed after %.2fs: %s",
                model,
                time.perf_counter() - t_model,
                e,
            )
    set_ready()
    logger.info(
        "warm_up_models done total_duration_sec=%.2f models=%s",
        time.perf_counter() - t0,
        len(model_names),
    )
