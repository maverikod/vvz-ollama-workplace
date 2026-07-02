"""
Shared exception classes for provider clients (AR-3 uniform error model).

All provider clients normalize transport/provider-specific errors into these
categories. Suitable for map_error(exception) to return or re-raise.
See docs/standards/provider_client_standard.md and CLIENT_UNIFICATION_TZ.md.

Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com
"""

from typing import Optional

__all__ = [
    "ProviderError",
    "TransportError",
    "AuthError",
    "TimeoutError",
    "RateLimitError",
    "ProviderProtocolError",
    "ValidationError",
    "CapabilityNotSupportedError",
]


class ProviderError(Exception):
    """Base for provider client errors. Message safe for logging and tool results."""

    def __init__(
        self,
        message: str,
        cause: Optional[BaseException] = None,
    ) -> None:
        """Store error message and optional cause for exception chaining."""
        super().__init__(message)
        self.message = message
        self.cause = cause
        if cause is not None:
            self.__cause__ = cause


class TransportError(ProviderError):
    """Network or transport failure (connection refused, DNS, TLS handshake, etc.)."""


class AuthError(ProviderError):
    """Auth failure (invalid credentials, expired token, etc.)."""


class TimeoutError(ProviderError):
    """Request or operation timed out. Provider context (distinct from built-in)."""


class RateLimitError(ProviderError):
    """Provider rate limit exceeded (HTTP 429 or equivalent)."""


class ProviderProtocolError(ProviderError):
    """Unexpected or malformed provider response (protocol/format violation)."""


class ValidationError(ProviderError):
    """Invalid request parameters or config (client-side validation failure)."""


class CapabilityNotSupportedError(ProviderError):
    """
    Raised when an operation is not supported (e.g. embed() on client with
    supports_embeddings=False). Per TZ: every client implements embed();
    unsupported = flag plus this error on call. No network call when raising.
    """
