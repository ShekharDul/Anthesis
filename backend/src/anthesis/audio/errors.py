"""Domain errors raised by Anthesis audio processing."""


class AudioProcessingError(ValueError):
    """Base class for audio input and preprocessing failures."""


class AudioNotFoundError(AudioProcessingError):
    """Raised when the requested audio path is not a regular file."""


class AudioDecodeError(AudioProcessingError):
    """Raised when libsndfile cannot decode the supplied media."""


class AudioLimitError(AudioProcessingError):
    """Raised when an input exceeds configured safety limits."""


class SilentAudioError(AudioProcessingError):
    """Raised when an input contains no usable audible signal."""


class AudioTooShortError(AudioProcessingError):
    """Raised when the usable signal is shorter than the configured minimum."""
