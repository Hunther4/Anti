"""
Anti Exception Hierarchy.

All custom exceptions in the project derive from AntiError.

Usage:
    from src.exceptions import ToolError, ProviderError, MemoryError

    raise ToolError("Sandbox execution failed")
"""


class AntiError(Exception):
    """Base exception for all Anti errors."""
    pass


class ToolError(AntiError):
    """Raised when a tool (e.g., search, file I/O, sandbox) fails."""
    pass


class ProviderError(AntiError):
    """Raised when an LLM provider fails (connection, auth, API error)."""
    pass


class MemoryError(AntiError):
    """Raised when memory or archive operations fail (read/write/query)."""
    pass


class BrainConnectionError(AntiError):
    """
    Raised when there is a connection issue with the LLM server.
    Defined here but also importable from src.brain for backward compat.
    """
    pass


class BrainContextError(AntiError):
    """
    Raised when context limits are exceeded or context sync fails.
    Defined here but also importable from src.brain for backward compat.
    """
    pass


class ConfigError(AntiError):
    """Raised for configuration issues (missing keys, invalid values)."""
    pass


# Backward-compatible aliases
# Import these from src.exceptions going forward.
BrainError = AntiError  # Base BrainError is just AntiError for clean hierarchy
