"""
Load rules, standards, and tools from disk for automatic context injection.
When files exist at configured paths, their content is used in context/tools.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def load_text_file(path: Optional[str]) -> Optional[str]:
    """
    Load file content as UTF-8 text if path is set and file exists.
    Returns None if path is empty, file missing, or read error.
    """
    if not path or not str(path).strip():
        return None
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        logger.debug("context_file_loader path not a file: %s", p)
        return None
    try:
        return p.read_text(encoding="utf-8").strip()
    except OSError as e:
        logger.warning("context_file_loader read failed path=%s error=%s", p, e)
        return None


def load_tools_json(path: Optional[str]) -> Optional[List[Dict[str, Any]]]:
    """
    Load a JSON array of OLLAMA-format tools from file if path is set and valid.
    Each item: type "function", function with name, description, parameters.
    Returns None if path empty, file missing, or invalid JSON/format.
    """
    if not path or not str(path).strip():
        return None
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        logger.debug("context_file_loader tools path not a file: %s", p)
        return None
    try:
        raw = p.read_text(encoding="utf-8").strip()
    except OSError as e:
        logger.warning("context_file_loader tools read failed path=%s error=%s", p, e)
        return None
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.warning("context_file_loader tools JSON invalid path=%s error=%s", p, e)
        return None
    if not isinstance(data, list):
        logger.warning("context_file_loader tools not a list path=%s", p)
        return None
    result: List[Dict[str, Any]] = []
    for i, item in enumerate(data):
        if (
            isinstance(item, dict)
            and item.get("type") == "function"
            and isinstance(item.get("function"), dict)
        ):
            result.append(item)
        else:
            logger.debug("context_file_loader tools item %s skipped (bad shape)", i)
    return result if result else None
