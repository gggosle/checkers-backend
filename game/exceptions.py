class GameDomainError(Exception):
    """Base exception for all game-related domain errors."""
    pass

class InvalidMoveError(GameDomainError):
    """Raised when a player attempts an illegal Checkers move."""
    pass