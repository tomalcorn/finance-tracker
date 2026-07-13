"""Errors raised by the SQL migration runner."""


class MigrationError(Exception):
    """Base class for all migration runner errors."""


class MigrationConfigError(MigrationError):
    """Raised when the runner cannot resolve its configuration (e.g. DB URL)."""


class MigrationDiscoveryError(MigrationError):
    """Raised when the migration files on disk are malformed or ambiguous."""
