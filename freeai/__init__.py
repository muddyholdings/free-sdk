"""Free.ai Python SDK — access 400+ AI tools from your code."""

# Read from the installed distribution rather than restated here. The two
# drifted immediately: pyproject went to 0.3.0 while this still said 0.2.0,
# so `freeai.__version__` reported the wrong release to anyone debugging --
# and a version a user quotes in a bug report is worth nothing if it is a
# second hardcoded copy of the real one.
try:
    from importlib.metadata import version as _pkg_version, PackageNotFoundError
    try:
        __version__ = _pkg_version("free-dot-ai")
    except PackageNotFoundError:  # running from a source checkout
        __version__ = "0.0.0.dev0"
except ImportError:  # Python < 3.8 has no importlib.metadata
    __version__ = "0.0.0.dev0"

from .client import FreeAI, AsyncFreeAI
from .exceptions import FreeAIError, AuthenticationError, RateLimitError, InsufficientCreditsError
from .models import (
    ChatResponse,
    ChatStreamChunk,
    ImageResponse,
    TTSResponse,
    TranslateResponse,
    STTResponse,
    OCRResponse,
    MusicResponse,
    VideoResponse,
)

__all__ = [
    "FreeAI",
    "AsyncFreeAI",
    "FreeAIError",
    "AuthenticationError",
    "RateLimitError",
    "InsufficientCreditsError",
    "ChatResponse",
    "ChatStreamChunk",
    "ImageResponse",
    "TTSResponse",
    "TranslateResponse",
    "STTResponse",
    "OCRResponse",
    "MusicResponse",
    "VideoResponse",
]
