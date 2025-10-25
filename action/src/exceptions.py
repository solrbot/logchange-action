"""
Custom exception hierarchy for Logchange Action
"""


class LogchangeException(Exception):
    """Base exception for all Logchange errors"""

    pass


class ConfigurationError(LogchangeException):
    """Raised when configuration is invalid or missing"""

    pass


class ValidationError(LogchangeException):
    """Raised when changelog entry validation fails"""

    pass


class GenerationError(LogchangeException):
    """Raised when Claude API generation fails"""

    pass


class GitHubError(LogchangeException):
    """Raised when GitHub API operations fail"""

    pass


class LegacyHandlingError(LogchangeException):
    """Raised when legacy changelog handling fails"""

    pass


class MetadataExtractionError(LogchangeException):
    """Raised when PR metadata extraction fails"""

    pass
