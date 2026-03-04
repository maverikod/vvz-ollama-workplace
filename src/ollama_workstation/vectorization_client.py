"""
Vectorization client: embed text for semantic relevance.

Implementations: EmbedProxyClient (via proxy) or
DirectEmbedVectorizationClient (direct to server, embed-client, WebSocket).

embed-client: use_push=True (WebSocket), no polling. See docs/standards.md §7.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .proxy_client import ProxyClient, ProxyClientError
from .server_resolver import get_server_url, server_url_to_embed_config_dict

if TYPE_CHECKING:
    from .config import WorkstationConfig

logger = logging.getLogger(__name__)


class VectorizationError(Exception):
    """Embedding call failed; message safe for logging."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class VectorizationClient(ABC):
    """
    Abstract client for text vectorization (embedding).
    Implementations use embed-client or equivalent service.
    """

    @abstractmethod
    async def embed_text(self, text: str) -> Optional[List[float]]:
        """
        Return embedding vector for a single text, or None on failure.
        Caller should fall back to non-vector ranking when None.
        """
        raise NotImplementedError

    async def embed_texts(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Return one embedding per text; None for failed items.
        Default: sequential embed_text; override for batch.
        """
        out: List[Optional[List[float]]] = []
        for t in texts:
            out.append(await self.embed_text(t))
        return out


def _parse_embedding_from_response(response: object) -> Optional[List[float]]:
    """
    Extract embedding list from embed service response.
    Expects content with JSON: {"embedding": [...], "model": "..."} or similar.
    """
    if not isinstance(response, dict):
        return None
    # Direct embedding key (e.g. result.embedding)
    emb = response.get("embedding")
    if isinstance(emb, list) and emb and isinstance(emb[0], (int, float)):
        return [float(x) for x in emb]
    # Nested in content (e.g. result.content as JSON string)
    content = response.get("content")
    if isinstance(content, str):
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                emb = data.get("embedding")
                if isinstance(emb, list) and emb and isinstance(emb[0], (int, float)):
                    return [float(x) for x in emb]
        except json.JSONDecodeError:
            pass
    return None


class EmbedProxyClient(VectorizationClient):
    """
    Vectorization client using embed-client via MCP proxy.
    Calls proxy call_server(embedding_server_id, embedding_command, {"text": text}).
    """

    def __init__(
        self,
        proxy_client: ProxyClient,
        embedding_server_id: str = "embedding-service",
        embedding_command: str = "embed",
    ) -> None:
        """Initialize with proxy client and embed service id/command."""
        self._proxy = proxy_client
        self._server_id = (embedding_server_id or "embedding-service").strip()
        self._command = (embedding_command or "embed").strip()

    async def embed_text(self, text: str) -> Optional[List[float]]:
        """
        Call embed service via proxy; return embedding or None on failure.
        Params: typically {"text": text}; service may expect "text" or "inputs".
        """
        if not (self._server_id and self._command):
            return None
        payload: dict = {"text": text}
        try:
            result = await self._proxy.call_server(
                server_id=self._server_id,
                command=self._command,
                copy_number=1,
                params=payload,
            )
        except ProxyClientError as e:
            logger.warning(
                "embed_text failed server_id=%s command=%s: %s",
                self._server_id,
                self._command,
                e.message,
            )
            return None
        if not isinstance(result, dict):
            return None
        # Some APIs return result inside "result" or "data"
        data = result.get("result", result.get("data", result))
        embedding = _parse_embedding_from_response(
            data if isinstance(data, dict) else result
        )
        if embedding is None:
            logger.debug(
                "embed_text no embedding in response keys=%s",
                list(result.keys()) if isinstance(result, dict) else None,
            )
        return embedding


class DirectEmbedVectorizationClient(VectorizationClient):
    """
    Vectorization client: direct connection to embedding service (embed-client).

    Resolves server_url from proxy list_servers; uses embed-client with
    WebSocket (use_push=True). No proxy call_server for embed.
    """

    def __init__(
        self,
        proxy_client: ProxyClient,
        config: "WorkstationConfig",
        embedding_server_id: str = "embedding-service",
        embedding_command: str = "embed",
    ) -> None:
        """Initialize with proxy (for list_servers), config (certs), server id."""
        self._proxy = proxy_client
        self._config = config
        self._server_id = (embedding_server_id or "embedding-service").strip()
        self._command = (embedding_command or "embed").strip()
        self._embed_client: Any = None
        self._server_url: Optional[str] = None

    async def _ensure_client(self) -> bool:
        """Resolve server_url from proxy and create embed-client; return True if ok."""
        if self._embed_client is not None:
            return True
        server_url = await get_server_url(
            self._proxy.list_servers,
            self._server_id,
        )
        if not server_url:
            logger.warning(
                "DirectEmbed: server_id=%s not found in list_servers",
                self._server_id,
            )
            return False
        self._server_url = server_url
        config_dict = server_url_to_embed_config_dict(server_url, self._config)
        try:
            from embed_client import EmbeddingServiceAsyncClient

            self._embed_client = EmbeddingServiceAsyncClient(config_dict=config_dict)
            return True
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "DirectEmbed: failed to create client server_id=%s: %s",
                self._server_id,
                e,
            )
            return False

    async def embed_text(self, text: str) -> Optional[List[float]]:
        """
        Embed one text via direct connection (embed-client, use_push=True).
        """
        if not (await self._ensure_client()) or self._embed_client is None:
            return None
        try:
            result = await self._embed_client.embed(
                [text],
                use_push=True,
                timeout=60.0,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "DirectEmbed embed_text failed server_id=%s: %s",
                self._server_id,
                e,
            )
            return None
        return _embed_result_to_single_vector(result)


def _embed_result_to_single_vector(result: Dict[str, Any]) -> Optional[List[float]]:
    """Extract first embedding from embed-client result (results or embeddings)."""
    if not isinstance(result, dict):
        return None
    # results[0].embedding (new format)
    results = result.get("results")
    if isinstance(results, list) and results:
        first = results[0]
        if isinstance(first, dict):
            emb = first.get("embedding")
            if isinstance(emb, list) and emb:
                return [float(x) for x in emb]
    # embeddings[0] (legacy)
    embeddings = result.get("embeddings")
    if isinstance(embeddings, list) and embeddings:
        emb = embeddings[0]
        if isinstance(emb, list) and emb:
            return [float(x) for x in emb]
    # result.result.data.results[0].embedding (adapter wrap)
    res = result.get("result", result)
    if isinstance(res, dict) and "data" in res:
        data = res["data"]
        if isinstance(data, dict) and "results" in data:
            arr = data["results"]
            if isinstance(arr, list) and arr and isinstance(arr[0], dict):
                emb = arr[0].get("embedding")
                if isinstance(emb, list) and emb:
                    return [float(x) for x in emb]
    return None


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """
    Cosine similarity in [-1, 1]. Larger = more similar.
    Use for ranking by semantic closeness (sort by score descending).
    """
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a <= 0 or norm_b <= 0:
        return 0.0
    return float(dot / (norm_a * norm_b))
