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


class JointWorkspaceInitializationError(WorkspaceError):
    """Raised when a joint account's workspace cannot be set up correctly."""


class JointDataAccessError(JointWorkspaceInitializationError):
    """Raised when a repository operation fails during joint workspace init."""


class BankOneOffsError(UseCaseError):
    """Base error for the bank_one_offs use case."""


class AmountToBankLTEZeroError(BankOneOffsError):
    """Error when the amount to bank for an item is less than or equal to zero."""

    def __init__(self, item_name: str) -> None:
        """Construct AmountToBankLTEZeroError."""
        self.item_name = item_name
        super().__init__(f"{item_name} has nothing to bank.")


class ContributionError(UseCaseError):
    """Base error for the contribute_to_joint use case."""


class ContributionAmountError(ContributionError):
    """Error when the contribution amount is less than or equal to zero."""

    def __init__(self, amount: float) -> None:
        """Construct ContributionAmountError."""
        self.amount = amount
        super().__init__(f"A contribution must be more than zero, got {amount}.")


class NoJointAccountToContributeToError(ContributionError):
    """Error when the contributing user belongs to no joint account."""

    def __init__(self, user_id: str) -> None:
        """Construct NoJointAccountToContributeToError."""
        self.user_id = user_id
        super().__init__(f"User {user_id!r} belongs to no joint account.")


class JointExpenseSourceNotFoundError(ContributionError):
    """Error when the hidden "Joint" expense source is missing for a user."""

    def __init__(self, user_id: str) -> None:
        """Construct JointExpenseSourceNotFoundError."""
        self.user_id = user_id
        super().__init__(f"User {user_id!r} has no 'Joint' expense source.")


class ContributionWriteError(ContributionError):
    """Error when a repository operation in the contribution flow fails."""


class SummaryError(UseCaseError):
    """Base error for the summarise_finances use case."""


class SummaryReadError(SummaryError):
    """Error when a repository read fails while summarising."""

    def __init__(self, aggregate: str) -> None:
        """Construct SummaryReadError."""
        self.aggregate = aggregate
        super().__init__(f"Could not read {aggregate} to summarise.")


class QuickPaymentError(UseCaseError):
    """Base error for the log_quick_payment use case."""


class QuickButtonNotFoundError(QuickPaymentError):
    """Error when the tapped quick button no longer exists."""

    def __init__(self, button_id: str) -> None:
        """Construct QuickButtonNotFoundError."""
        self.button_id = button_id
        super().__init__(f"No quick button with id {button_id!r}.")


class IncompleteQuickPaymentError(QuickPaymentError):
    """Error when a tap leaves a payment field neither preset nor supplied."""

    def __init__(self, button_name: str, missing: list[str]) -> None:
        """Construct IncompleteQuickPaymentError."""
        self.button_name = button_name
        self.missing = missing
        joined = ", ".join(missing)
        super().__init__(
            f"Quick button {button_name!r} cannot log a payment without {joined}.",
        )


class QuickPaymentWriteError(QuickPaymentError):
    """Error when a repository operation in the quick-payment flow fails."""


class UserSettingsError(UseCaseError):
    """Base error for the manage_user_settings use case."""


class UserSettingsReadError(UserSettingsError):
    """Error when the settings row could not be read or defaulted."""


class UserSettingsWriteError(UserSettingsError):
    """Error when a settings change could not be persisted."""
