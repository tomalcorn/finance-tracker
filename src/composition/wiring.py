"""Factory functions for constructing use cases with live dependencies."""

from adapters.supabase import repository as supabase_repos
from libs import auth, data_client
from use_cases.reconcile_subscriptions import ReconcileSubscriptionsUseCase


def reconcile_subscriptions_use_case() -> ReconcileSubscriptionsUseCase:
    """Build ReconcileSubscriptionsUseCase wired to Supabase repositories."""
    connection = data_client.CONN
    user_id = auth.get_current_user()
    return ReconcileSubscriptionsUseCase(
        subscription_repo=supabase_repos.SupabaseSubscriptionRepository(
            connection,
            user_id,
        ),
        payment_repo=supabase_repos.SupabasePaymentRepository(connection, user_id),
    )
