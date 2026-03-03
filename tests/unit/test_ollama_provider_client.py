"""
Unit tests for OllamaProviderClient (step_08).

Covers: validate_config errors, embed when supports_embeddings=False,
map_error for 401/403/429/timeout/network, normalize_response.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from ollama_workstation.ollama_provider_client import (  # noqa: E402
    OllamaProviderClient,
)
from ollama_workstation.provider_errors import (  # noqa: E402
    AuthError,
    CapabilityNotSupportedError,
    ProviderProtocolError,
    RateLimitError,
    TimeoutError as ProviderTimeoutError,
    TransportError,
    ValidationError,
)


def _valid_config(
    base_url: str = "http://localhost:11434", timeout: float = 60.0
) -> Dict[str, Any]:
    """Minimal valid Ollama provider section."""
    return {
        "transport": {
            "base_url": base_url,
            "request_timeout_seconds": timeout,
        },
    }


# --- validate_config ---


def test_validate_config_empty_base_url_raises() -> None:
    """validate_config() raises ValidationError when transport.base_url is empty."""
    config = {"transport": {"base_url": ""}}
    client = OllamaProviderClient(config)
    with pytest.raises(ValidationError) as exc_info:
        client.validate_config()
    assert (
        "base_url" in str(exc_info.value).lower()
        or "required" in str(exc_info.value).lower()
    )


def test_validate_config_missing_base_url_raises() -> None:
    """validate_config() raises ValidationError when transport has no base_url."""
    config: Dict[str, Any] = {"transport": {}}
    client = OllamaProviderClient(config)
    with pytest.raises(ValidationError):
        client.validate_config()


def test_validate_config_negative_timeout_raises() -> None:
    """validate_config() raises ValidationError when request_timeout_seconds <= 0."""
    config = {
        "transport": {
            "base_url": "http://localhost:11434",
            "request_timeout_seconds": 0,
        },
    }
    client = OllamaProviderClient(config)
    with pytest.raises(ValidationError) as exc_info:
        client.validate_config()
    assert (
        "timeout" in str(exc_info.value).lower()
        or "positive" in str(exc_info.value).lower()
    )


def test_validate_config_valid_passes() -> None:
    """validate_config() does not raise when base_url and timeout are valid."""
    client = OllamaProviderClient(_valid_config())
    client.validate_config()


# --- supports_embeddings=False -> CapabilityNotSupportedError, no HTTP ---


def test_embed_when_supports_embeddings_false_raises_no_http() -> None:
    """supports_embeddings=False: embed raises CapabilityNotSupportedError, no HTTP."""
    config = {
        "transport": {"base_url": "http://localhost:11434"},
        "features": {"supports_embeddings": False},
    }
    client = OllamaProviderClient(config)
    assert client.supports_embeddings is False
    with pytest.raises(CapabilityNotSupportedError) as exc_info:
        client.embed({"model": "nomic-embed", "input": "hello"})
    assert (
        "embed" in str(exc_info.value).lower()
        or "not supported" in str(exc_info.value).lower()
    )
    # No HTTP: _get_client() would be called only if we passed the guard; we didn't.
    assert client._http_client is None


# --- map_error ---


def _make_http_status_error(status_code: int) -> httpx.HTTPStatusError:
    """Build HTTPStatusError with given status code."""
    req = MagicMock(spec=httpx.Request)
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    return httpx.HTTPStatusError("error", request=req, response=resp)


def test_map_error_401_returns_auth_error() -> None:
    """map_error(HTTPStatusError 401) returns AuthError."""
    client = OllamaProviderClient(_valid_config())
    err = _make_http_status_error(401)
    mapped = client.map_error(err)
    assert isinstance(mapped, AuthError)


def test_map_error_403_returns_auth_error() -> None:
    """map_error(HTTPStatusError 403) returns AuthError."""
    client = OllamaProviderClient(_valid_config())
    err = _make_http_status_error(403)
    mapped = client.map_error(err)
    assert isinstance(mapped, AuthError)


def test_map_error_429_returns_rate_limit_error() -> None:
    """map_error(HTTPStatusError 429) returns RateLimitError."""
    client = OllamaProviderClient(_valid_config())
    err = _make_http_status_error(429)
    mapped = client.map_error(err)
    assert isinstance(mapped, RateLimitError)


def test_map_error_timeout_returns_timeout_error() -> None:
    """map_error(httpx.TimeoutException) returns TimeoutError (provider)."""
    client = OllamaProviderClient(_valid_config())
    err = httpx.TimeoutException("timed out")
    mapped = client.map_error(err)
    assert isinstance(mapped, ProviderTimeoutError)


def test_map_error_connect_error_returns_transport_error() -> None:
    """map_error(httpx.ConnectError) returns TransportError."""
    client = OllamaProviderClient(_valid_config())
    err = httpx.ConnectError("connection refused")
    mapped = client.map_error(err)
    assert isinstance(mapped, TransportError)


def test_map_error_network_error_returns_transport_error() -> None:
    """map_error(httpx.NetworkError) returns TransportError."""
    client = OllamaProviderClient(_valid_config())
    err = httpx.NetworkError("network error")
    mapped = client.map_error(err)
    assert isinstance(mapped, TransportError)


def test_map_error_already_provider_error_returns_same() -> None:
    """map_error(ProviderError) returns the same instance."""
    client = OllamaProviderClient(_valid_config())
    original = ValidationError("already validated")
    mapped = client.map_error(original)
    assert mapped is original


# --- normalize_response ---


def test_normalize_response_valid_chat() -> None:
    """normalize_response() returns message and token counts for valid chat."""
    client = OllamaProviderClient(_valid_config())
    raw = {
        "message": {"role": "assistant", "content": "Hi"},
        "prompt_eval_count": 10,
        "eval_count": 2,
    }
    out = client.normalize_response(raw)
    assert out["message"] == raw["message"]
    assert out["prompt_eval_count"] == 10
    assert out["eval_count"] == 2


def test_normalize_response_missing_message_raises() -> None:
    """normalize_response() raises ProviderProtocolError when 'message' is missing."""
    client = OllamaProviderClient(_valid_config())
    raw = {"prompt_eval_count": 1}
    with pytest.raises(ProviderProtocolError) as exc_info:
        client.normalize_response(raw)
    assert "message" in str(exc_info.value).lower()


def test_normalize_response_not_dict_raises() -> None:
    """normalize_response() raises ProviderProtocolError when raw is not a dict."""
    client = OllamaProviderClient(_valid_config())
    with pytest.raises(ProviderProtocolError):
        client.normalize_response("not a dict")


# --- capability flags and supports_tools ---


def test_supports_tools_true() -> None:
    """OllamaProviderClient.supports_tools() returns True."""
    client = OllamaProviderClient(_valid_config())
    assert client.supports_tools() is True


def test_supports_stream_default_true() -> None:
    """supports_stream is True by default."""
    client = OllamaProviderClient(_valid_config())
    assert client.supports_stream is True


def test_supports_embeddings_default_true() -> None:
    """supports_embeddings is True when not set in features."""
    client = OllamaProviderClient(_valid_config())
    assert client.supports_embeddings is True
