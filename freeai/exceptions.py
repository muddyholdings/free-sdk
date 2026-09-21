"""Exceptions for the Free.ai SDK."""


class FreeAIError(Exception):
    """Base exception for Free.ai SDK errors."""

    def __init__(self, message: str, status_code: int = None, error_id: str = None,
                 details: dict = None):
        self.message = message
        self.status_code = status_code
        self.error_id = error_id
        #: Structured fields the API returned alongside the message, when it
        #: sent any -- e.g. ``requires_signup`` and ``daily_remaining`` on a
        #: 429. Always a dict, so callers can ``.get()`` without guarding.
        self.details = details or {}
        super().__init__(message)

    def __str__(self):
        # The error_id is what support can actually look up, so it belongs in
        # the text a traceback prints, not only on an attribute nobody reads.
        if self.error_id:
            return "%s (error_id: %s)" % (self.message, self.error_id)
        return self.message


class AuthenticationError(FreeAIError):
    """Raised when the API key is invalid or missing."""
    pass


class RateLimitError(FreeAIError):
    """Raised when rate limits are exceeded."""
    pass


class InsufficientCreditsError(FreeAIError):
    """Raised when the account has insufficient tokens/credits."""
    pass
