"""Custom errors for the Use Cases."""


class UseCaseError(Exception):
    """Base error for all use cases."""


class ReconciliationError(UseCaseError):
    """Base error for the reconcile_subscriptions use case."""


class InvalidCadenceError(ReconciliationError):
    """Error when the specified Cadence is not known."""

    def __init__(self, cadence: str) -> None:
        """Construct InvalidCadenceError."""
        self.cadence = cadence
        super().__init__(f"Unknown cadence: {cadence}")
