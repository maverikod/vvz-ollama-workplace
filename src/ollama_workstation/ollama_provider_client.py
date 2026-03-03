"""
Concrete Ollama provider client (unified workstation API).

Implements BaseProviderClient for Ollama: chat, embed, healthcheck, config
validation. Transport and auth details are internal; workstation sees only
the common API. See step_08 and docs/standards/provider_client_standard.md.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx

from .provider_client_base import BaseProviderClient
from .provider_errors import (
    AuthError,
    CapabilityNotSupportedError,
    ProviderError,
    ProviderProtocolError,
    RateLimitError,
    TimeoutError as ProviderTimeoutError,
    TransportError,
    ValidationError,
)

logger = logging.getLogger(__name__)

# Default request timeout when not set in config (seconds).
DEFAULT_REQUEST_TIMEOUT = 60.0


class OllamaProviderClient(BaseProviderClient):
    """
    Ollama provider client: chat and embed via Ollama HTTP API.

    Config is the provider section (e.g. provider_clients.providers.ollama)
    with required transport.base_url and optional transport.request_timeout_seconds.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Store provider section config. Call validate_config() before use.

        Args:
            config: Provider section dict with at least transport.base_url.
        """
        self._config = dict(config) if config else {}
        self._transport = self._config.get("transport") or {}
        self._base_url = (self._transport.get("base_url") or "").strip().rstrip("/")
        timeout_val = self._transport.get("request_timeout_seconds")
        if timeout_val is not None and isinstance(timeout_val, (int, float)):
            self._timeout = float(timeout_val)
        else:
            self._timeout = DEFAULT_REQUEST_TIMEOUT
        self._features = self._config.get("features") or {}
        # Capability flags: Ollama supports stream, tools, embeddings.
        self._supports_stream = self._features.get("supports_stream", True)
        self._supports_embeddings_flag = self._features.get("supports_embeddings", True)
        self._http_client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        """Return a sync HTTP client; create and cache on first use."""
        if self._http_client is None:
            self._http_client = httpx.Client(timeout=self._timeout)
        return self._http_client

    @property
    def supports_stream(self) -> bool:
        """Whether the client can return streaming chat responses."""
        return bool(self._supports_stream)

    def supports_tools(self) -> bool:
        """Report whether the client supports tool/function calling."""
        return True

    @property
    def supports_embeddings(self) -> bool:
        """Whether the client supports embedding requests."""
        return bool(self._supports_embeddings_flag)

    def validate_config(self) -> None:
        """
        Validate client configuration before use.

        Raises ValidationError if base_url is missing or invalid.
        MUST NOT perform network I/O.
        """
        if not self._base_url:
            raise ValidationError(
                "Ollama provider config: transport.base_url is required and non-empty."
            )
        if self._timeout <= 0:
            raise ValidationError(
                "Ollama provider config: request_timeout_seconds must be positive."
            )

    def healthcheck(self) -> bool:
        """
        Check that the Ollama endpoint is reachable (GET /api/tags).

        Returns True if 200, False otherwise. Maps exceptions via map_error.
        """
        try:
            client = self._get_client()
            url = f"{self._base_url}/api/tags"
            resp = client.get(url)
            if resp.status_code == 200:
                return True
            err = httpx.HTTPStatusError(
                "Ollama healthcheck failed",
                request=resp.request,
                response=resp,
            )
            mapped = self.map_error(err)
            logger.warning(
                "Ollama healthcheck non-200 status=%s: %s",
                resp.status_code,
                mapped.message,
            )
            return False
        except Exception as e:
            mapped = self.map_error(e)
            logger.warning(
                "Ollama healthcheck failed: %s",
                mapped.message,
                exc_info=False,
            )
            return False

    def chat(self, request: Any) -> Any:
        """
        Send a chat request to Ollama (POST /api/chat).

        Request must contain model, messages; optional tools, stream.
        Returns normalized response (message, prompt_eval_count, eval_count).
        """
        if not isinstance(request, dict):
            raise ValidationError(
                "Chat request must be a dict with model and messages."
            )
        model = request.get("model")
        messages = request.get("messages")
        if not model or not isinstance(messages, list):
            raise ValidationError(
                "Chat request must include model (non-empty) and messages (list)."
            )
        body: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if "tools" in request and request["tools"]:
            body["tools"] = request["tools"]
        try:
            client = self._get_client()
            url = f"{self._base_url}/api/chat"
            resp = client.post(url, json=body)
            resp.raise_for_status()
            raw = resp.json()
            return self.normalize_response(raw)
        except httpx.HTTPStatusError as e:
            raise self.map_error(e)
        except Exception as e:
            raise self.map_error(e)

    def embed(self, request: Any) -> Any:
        """
        Request embeddings from Ollama (POST /api/embed).

        If supports_embeddings is False, raises CapabilityNotSupportedError
        without network call. Request: model and input (string or list of strings).
        """
        if not self._supports_embeddings_flag:
            raise CapabilityNotSupportedError(
                "Ollama provider client has supports_embeddings=False; "
                "embed is not supported."
            )
        if not isinstance(request, dict):
            raise ValidationError("Embed request must be a dict with model and input.")
        model = request.get("model")
        inp = request.get("input")
        if not model:
            raise ValidationError("Embed request must include model.")
        if inp is None:
            raise ValidationError(
                "Embed request must include input (string or list of strings)."
            )
        body: Dict[str, Any] = {"model": model, "input": inp}
        try:
            client = self._get_client()
            url = f"{self._base_url}/api/embed"
            resp = client.post(url, json=body)
            resp.raise_for_status()
            raw = resp.json()
            return self._normalize_embed_response(raw)
        except httpx.HTTPStatusError as e:
            raise self.map_error(e)
        except Exception as e:
            raise self.map_error(e)

    def normalize_response(self, raw_response: Any) -> Any:
        """
        Convert Ollama /api/chat response to workstation-standard shape.

        Expects dict: message (role, content, tool_calls), prompt_eval_count,
        eval_count.
        """
        if not isinstance(raw_response, dict):
            raise ProviderProtocolError(
                "Ollama chat response must be a JSON object.",
                cause=raw_response if isinstance(raw_response, BaseException) else None,
            )
        message = raw_response.get("message")
        if message is None:
            raise ProviderProtocolError(
                "Ollama chat response missing 'message' field.",
            )
        return {
            "message": message,
            "prompt_eval_count": raw_response.get("prompt_eval_count"),
            "eval_count": raw_response.get("eval_count"),
        }

    def _normalize_embed_response(self, raw: Any) -> Any:
        """Convert Ollama /api/embed response to workstation-standard shape."""
        if not isinstance(raw, dict):
            raise ProviderProtocolError(
                "Ollama embed response must be a JSON object.",
                cause=raw if isinstance(raw, BaseException) else None,
            )
        embeddings = raw.get("embeddings")
        if embeddings is None:
            raise ProviderProtocolError(
                "Ollama embed response missing 'embeddings'."
            )
        return {
            "embeddings": embeddings,
            "model": raw.get("model"),
            "prompt_eval_count": raw.get("prompt_eval_count"),
        }

    def map_error(self, exception: BaseException) -> ProviderError:
        """
        Map httpx or provider exception to a standard ProviderError.

        Returns the appropriate error; caller may re-raise.
        """
        if isinstance(exception, ProviderError):
            return exception
        if isinstance(exception, httpx.HTTPStatusError):
            code = exception.response.status_code if exception.response else 0
            msg = getattr(exception, "message", str(exception))
            if code == 401 or code == 403:
                return AuthError(msg, cause=exception)
            if code == 429:
                return RateLimitError(msg, cause=exception)
            if code >= 400:
                return ProviderProtocolError(msg, cause=exception)
        if isinstance(exception, httpx.TimeoutException):
            return ProviderTimeoutError(
                "Ollama request timed out.",
                cause=exception,
            )
        if isinstance(exception, (httpx.ConnectError, httpx.NetworkError)):
            return TransportError(str(exception), cause=exception)
        return TransportError(str(exception), cause=exception)
