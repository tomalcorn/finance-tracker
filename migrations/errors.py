"""Errors raised by the SQL migration runner."""


class MigrationError(Exception):
    """Base class for all migration runner errors."""


class MigrationDiscoveryError(MigrationError):
    """Raised when the migration files on disk are malformed or ambiguous."""
