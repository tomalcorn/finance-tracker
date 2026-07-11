"""Custom errors for the domain."""


class DomainError(Exception):
    """Base error for other DomainErrors to inherit from."""


class RepositoryError(DomainError):
    """Raised when a repository operation fails to read or write an aggregate.

    Crosses the repository/grid port as a domain-level error so both use cases
    and the UI can catch it without importing the driven adapter. The concrete
    adapter translates its own low-level failures (Supabase, cache, HTTP) into
    this type at the port boundary.
    """


class InvalidSubscriptionCadenceError(DomainError):
    """Error when a provided cadence isn't recognised."""

    def __init__(self, cadence: str) -> None:
        """Construct InvalidSubscriptionCadenceError."""
        self.cadence = cadence
        super().__init__(f"Unknown cadence: {cadence}")
