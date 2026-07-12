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


class WorkspaceError(UseCaseError):
    """Base for workspace initialisation errors."""


class WorkspaceInitializationError(WorkspaceError):
    """Raised when the workspace cannot be set up correctly."""


class DataAccessError(WorkspaceInitializationError):
    """Raised when a repository operation fails."""


class BankOneOffsError(UseCaseError):
    """Base error for the bank_one_offs use case."""


class AmountToBankLTEZeroError(BankOneOffsError):
    """Error when the amount to bank for an item is less than or equal to zero."""

    def __init__(self, item_name: str) -> None:
        """Construct AmountToBankLTEZeroError."""
        self.item_name = item_name
        super().__init__(f"{item_name} has nothing to bank.")
