class AIEngineError(Exception):
    """Base exception for AI engine failures."""


class AITimeoutError(AIEngineError):
    """Raised when provider call times out or is rate-limited."""


class AIHallucinationError(AIEngineError):
    """Raised when provider returns invalid or illegal move payload."""


class AIConfigurationError(AIEngineError):
    """Raised when provider configuration is invalid."""
