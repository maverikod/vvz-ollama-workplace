"""
Abstract base class for provider clients (unified workstation API).

Defines the contract from docs/standards/provider_client_standard.md.
All provider clients must implement required methods and capability flags.
Uses provider_errors from step_03 for error mapping.
See CLIENT_UNIFICATION_TZ.md and SCOPE_FREEZE (provider_client_base.py).

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from abc import ABC, abstractmethod
from typing import Any

from .provider_errors import ProviderError


class BaseProviderClient(ABC):
    """
    Abstract base for all provider clients.

    Workstation communicates with model providers only through this interface.
    Transport, protocol, and auth details are internal to concrete clients.
    """

    # --- Capability flags (constant for client lifetime) ---

    @property
    @abstractmethod
    def supports_stream(self) -> bool:
        """Whether the client can return streaming chat responses."""
        raise NotImplementedError

    @abstractmethod
    def supports_tools(self) -> bool:
        """Report whether the client supports tool/function calling."""
        raise NotImplementedError

    @property
    @abstractmethod
    def supports_embeddings(self) -> bool:
        """
        Whether the client supports embedding requests.

        If False, embed() raises CapabilityNotSupportedError.
        """
        raise NotImplementedError

    # --- Lifecycle and config ---

    @abstractmethod
    def validate_config(self) -> None:
        """
        Validate client configuration before use.

        Raises nothing if config is valid.
        Raises ValidationError (or subtype from provider_errors) if invalid.
        MUST NOT perform network I/O.
        """
        raise NotImplementedError

    @abstractmethod
    def healthcheck(self) -> bool:
        """
        Check that the provider endpoint is reachable and acceptable.

        May perform a lightweight network call.
        Must map provider/transport failures via map_error.
        Returns True if healthy, False otherwise.
        """
        raise NotImplementedError

    # --- Chat and embed ---

    @abstractmethod
    def chat(self, request: Any) -> Any:
        """
        Send a chat (completion) request to the provider.

        Accepts workstation-standard chat request.
        Returns normalized response (use normalize_response internally).
        Must respect timeout/retry rules and use map_error for exceptions.
        """
        raise NotImplementedError

    @abstractmethod
    def embed(self, request: Any) -> Any:
        """
        Request embeddings for the given input.

        Mandatory for all clients. If supports_embeddings is False,
        must raise CapabilityNotSupportedError without network call.
        """
        raise NotImplementedError

    # --- Response and error mapping ---

    @abstractmethod
    def normalize_response(self, raw_response: Any) -> Any:
        """
        Convert provider-specific raw response to workstation-standard shape.

        Invalid or unexpected shapes may raise ProviderProtocolError or ValidationError.
        """
        raise NotImplementedError

    @abstractmethod
    def map_error(self, exception: BaseException) -> ProviderError:
        """
        Map a provider or transport exception to a standard error category.

        Accepts exception from HTTP client, SDK, or provider API.
        Returns or raises one of: TransportError, AuthError, TimeoutError,
        RateLimitError, ProviderProtocolError, ValidationError,
        CapabilityNotSupportedError. Caller may re-raise the returned error.
        """
        raise NotImplementedError
