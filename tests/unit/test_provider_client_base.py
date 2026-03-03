"""
Unit tests for BaseProviderClient (step_04 abstract base class).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from ollama_workstation.provider_client_base import BaseProviderClient  # noqa: E402
from ollama_workstation.provider_errors import (  # noqa: E402
    CapabilityNotSupportedError,
    TransportError,
)


def test_base_provider_client_importable() -> None:
    """BaseProviderClient is importable from ollama_workstation."""
    assert BaseProviderClient is not None
    assert hasattr(BaseProviderClient, "validate_config")
    assert hasattr(BaseProviderClient, "healthcheck")
    assert hasattr(BaseProviderClient, "chat")
    assert hasattr(BaseProviderClient, "embed")
    assert hasattr(BaseProviderClient, "supports_tools")
    assert hasattr(BaseProviderClient, "normalize_response")
    assert hasattr(BaseProviderClient, "map_error")
    assert hasattr(BaseProviderClient, "supports_stream")
    assert hasattr(BaseProviderClient, "supports_embeddings")


def test_concrete_subclass_implements_contract() -> None:
    """Minimal concrete subclass implements the base contract."""

    class StubProviderClient(BaseProviderClient):
        """Minimal implementation for testing the base contract."""

        @property
        def supports_stream(self) -> bool:
            return False

        def supports_tools(self) -> bool:
            return False

        @property
        def supports_embeddings(self) -> bool:
            return False

        def validate_config(self) -> None:
            pass

        def healthcheck(self) -> bool:
            return True

        def chat(self, request: Any) -> Any:
            return {"message": "", "finish_reason": "stop"}

        def embed(self, request: Any) -> Any:
            raise CapabilityNotSupportedError("Embeddings not supported", cause=None)

        def normalize_response(self, raw_response: Any) -> Any:
            return raw_response

        def map_error(self, exception: BaseException) -> Any:
            return TransportError(str(exception), cause=exception)

    client = StubProviderClient()
    assert client.supports_stream is False
    assert client.supports_tools() is False
    assert client.supports_embeddings is False
    client.validate_config()
    assert client.healthcheck() is True
    assert client.chat({}) == {"message": "", "finish_reason": "stop"}
    with pytest.raises(CapabilityNotSupportedError):
        client.embed({})
    err = client.map_error(ValueError("test"))
    assert err is not None
