"""Custom errors for the domain."""


class DomainError(Exception):
    """Base error for other DomainErrors to inherit from."""


class InvalidSubscriptionCadenceError(DomainError):
    """Error when a provided cadence isn't recognised."""

    def __init__(self, cadence: str) -> None:
        """Construct InvalidSubscriptionCadenceError."""
        self.cadence = cadence
        super().__init__(f"Unknown cadence: {cadence}")


class MissingJointAccountError(DomainError):
    """Error when a joint-owned item has no joint account reference."""

    def __init__(self) -> None:
        """Construct MissingJointAccountError."""
        super().__init__("joint_account_id is required when ownership_type is joint")
