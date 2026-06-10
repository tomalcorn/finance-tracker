"""Factory functions for constructing use cases with live dependencies."""

from adapters.supabase import repository as supabase_repos
from libs import auth, data_client
from use_cases import initialise_workspace, reconcile_subscriptions


def reconcile_subscriptions_use_case() -> (
    reconcile_subscriptions.ReconcileSubscriptionsUseCase
):
    """Build ReconcileSubscriptionsUseCase wired to Supabase repositories."""
    connection = data_client.CONN
    user_id = auth.get_current_user()
    return reconcile_subscriptions.ReconcileSubscriptionsUseCase(
        subscription_repo=supabase_repos.SupabaseSubscriptionRepository(
            connection,
            user_id,
        ),
        payment_repo=supabase_repos.SupabasePaymentRepository(connection, user_id),
    )


def workspace_init_use_case() -> initialise_workspace.InitialiseUserWorkspaceUseCase:
    """Build InitializeUserWorkspaceUseCase wired to Supabase repositories."""
    current_user = auth.get_current_user()
    return initialise_workspace.InitialiseUserWorkspaceUseCase(
        user_id=current_user,
        budget_tracker_repo=supabase_repos.SupabaseBudgetTrackerRepository(
            connection=data_client.CONN,
            user_id=current_user,
        ),
        expense_source_repo=supabase_repos.SupabaseExpenseSourceRepository(
            connection=data_client.CONN,
            user_id=current_user,
        ),
    )
