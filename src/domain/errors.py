"""Custom errors for the domain."""


class DomainError(Exception):
    """Base error for other DomainErrors to inherit from."""


class InvalidSubscriptionCadenceError(DomainError):
    """Error when a provided cadence isn't recognised."""

    def __init__(self, cadence: str) -> None:
        """Construct InvalidSubscriptionCadenceError."""
        self.cadence = cadence
        super().__init__(f"Unknown cadence: {cadence}")


class IncompleteQuickButtonError(DomainError):
    """Error when a log-on-tap quick button is missing a payment field."""

    def __init__(self, name: str, missing: list[str]) -> None:
        """Construct IncompleteQuickButtonError."""
        self.name = name
        self.missing = missing
        joined = ", ".join(missing)
        super().__init__(
            f"Quick button {name!r} logs on tap, so it needs {joined}. "
            "Set it to ask for details instead, or fill them in.",
        )


class MissingJointAccountError(DomainError):
    """Error when a joint-owned item has no joint account reference."""

    def __init__(self) -> None:
        """Construct MissingJointAccountError."""
        super().__init__("joint_account_id is required when ownership_type is joint")
