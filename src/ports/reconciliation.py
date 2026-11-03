"""Port for keeping subscription-generated payments in step with subscriptions."""

from typing import Protocol


class SubscriptionReconciler(Protocol):
    """Reconcile one half of the current user's finances."""

    def reconcile_subscriptions(self) -> None:
        """Book each subscription's next payment and remove any no longer due.

        Raises:
            RepositoryError: The reconciliation did not complete.

        """
        ...
