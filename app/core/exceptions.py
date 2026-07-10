class QuranBotError(Exception):
    """Base application exception."""


class ConfigurationError(QuranBotError):
    """Configuration is invalid."""


class NatiqAPIError(QuranBotError):
    """Natiq API request failed."""


class AuthenticationError(NatiqAPIError):
    """Authentication failed."""


class ResourceNotFound(NatiqAPIError):
    """Requested resource does not exist."""


class DatabaseError(QuranBotError):
    """Database operation failed."""


class CacheError(QuranBotError):
    """Redis operation failed."""
