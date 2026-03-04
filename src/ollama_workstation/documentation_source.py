"""
DocumentationSource interface and DirectoryDocumentationSource; step 11.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional


class DocumentationSource(ABC):
    """
    Interface: list_items (TOC) and get_content by item_id.
    Same for pre-fill and for documentation tool used by the model.
    """

    @abstractmethod
    def list_items(
        self,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return TOC: list of { id, title, description?, canon?: bool }.
        """
        raise NotImplementedError

    @abstractmethod
    def get_content(self, item_id: str) -> str:
        """Return raw text content for item_id."""
        raise NotImplementedError


class DirectoryDocumentationSource(DocumentationSource):
    """
    Backend: list files under docs_path; get_content reads file by path.
    """

    def __init__(self, docs_path: str) -> None:
        """Initialize with directory path (e.g. docs/)."""
        self._root = Path(docs_path).resolve() if docs_path else Path(".")

    def list_items(
        self,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List files under docs_path as TOC entries (id = relative path)."""
        out: List[Dict[str, Any]] = []
        if not self._root.is_dir():
            return out
        for p in sorted(self._root.rglob("*")):
            if p.is_file() and p.suffix in (".md", ".txt", ".rst"):
                rel = p.relative_to(self._root)
                item_id = str(rel).replace("\\", "/")
                out.append(
                    {
                        "id": item_id,
                        "title": p.stem,
                        "description": "",
                        "canon": True,
                    }
                )
        return out

    def get_content(self, item_id: str) -> str:
        """Read file content by relative path (item_id)."""
        safe = Path(item_id.replace("..", "").lstrip("/"))
        full = (self._root / safe).resolve()
        if not str(full).startswith(str(self._root)):
            return ""
        if not full.is_file():
            return ""
        return full.read_text(encoding="utf-8", errors="replace")
