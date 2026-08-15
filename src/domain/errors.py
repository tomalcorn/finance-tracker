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


class ZeroQuickButtonAmountError(DomainError):
    """Error when a quick button presets an amount of zero."""

    def __init__(self, name: str) -> None:
        """Construct ZeroQuickButtonAmountError."""
        self.name = name
        super().__init__(
            f"Quick button {name!r} presets an amount of zero, which would log a "
            "payment that moves no money. Set an amount, or leave it blank for a "
            "button that asks at the till.",
        )


class IncompleteJointContributionError(DomainError):
    """Error when a joint-contribution subscription is missing a joint field."""

    def __init__(self, name: str, missing: list[str]) -> None:
        """Construct IncompleteJointContributionError."""
        self.name = name
        self.missing = missing
        joined = ", ".join(missing)
        super().__init__(
            f"Subscription {name!r} contributes to a joint account, so it needs "
            f"{joined}.",
        )


class JointOwnedContributionError(DomainError):
    """Error when a joint-owned subscription claims to be a contribution."""

    def __init__(self, name: str) -> None:
        """Construct JointOwnedContributionError."""
        self.name = name
        super().__init__(
            f"Subscription {name!r} is owned by the joint account, so it cannot "
            "also contribute to one.",
        )


class IncompleteMultiMonthCategoryError(DomainError):
    """Error when a category's accrual and its amount columns disagree."""

    def __init__(self, name: str, missing: list[str]) -> None:
        """Construct IncompleteMultiMonthCategoryError."""
        self.name = name
        self.missing = missing
        joined = ", ".join(missing)
        super().__init__(
            f"Category {name!r} accrues across months, so it needs {joined}.",
        )


class MonthlyCategoryWithPotFieldsError(DomainError):
    """Error when a monthly category carries pot amounts it cannot use."""

    def __init__(self, name: str, present: list[str]) -> None:
        """Construct MonthlyCategoryWithPotFieldsError."""
        self.name = name
        self.present = present
        joined = ", ".join(present)
        super().__init__(
            f"Category {name!r} resets each month, so {joined} would never be "
            "read. Set it to accrue across months, or clear them.",
        )


class MultiMonthRootCategoryError(DomainError):
    """Error when a top-level category is set to accrue across months."""

    def __init__(self, name: str) -> None:
        """Construct MultiMonthRootCategoryError."""
        self.name = name
        super().__init__(
            f"Category {name!r} is top-level, so it is a monthly allowance and "
            "cannot accrue across months. Only a subcategory can be a pot.",
        )


class SelfParentedCategoryError(DomainError):
    """Error when a category names itself as its own parent."""

    def __init__(self, name: str) -> None:
        """Construct SelfParentedCategoryError."""
        self.name = name
        super().__init__(f"Category {name!r} cannot be its own parent.")


class MissingJointAccountError(DomainError):
    """Error when a joint-owned item has no joint account reference."""

    def __init__(self) -> None:
        """Construct MissingJointAccountError."""
        super().__init__("joint_account_id is required when ownership_type is joint")
