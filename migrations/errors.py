"""Errors raised by the SQL migration runner."""


class MigrationError(Exception):
    """Base class for all migration runner errors."""


class MigrationDiscoveryError(MigrationError):
    """Raised when the migration files on disk are malformed or ambiguous."""


class MissingDatabaseUrlError(MigrationError):
    """Raised when no connection URL is configured for the target environment."""

    def __init__(self, env: str, variable: str) -> None:
        """Construct MissingDatabaseUrlError.

        Args:
            env: The environment that was targeted (e.g. ``"testing"``).
            variable: The environment variable expected to hold its URL.

        """
        self.env = env
        self.variable = variable
        super().__init__(
            f"No database URL configured for env {env!r}; "
            f"set {variable} via the environment, or .env file.",
        )
