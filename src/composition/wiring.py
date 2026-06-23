"""Factory functions for constructing use cases with live dependencies."""

from typing import TYPE_CHECKING

from adapters.supabase import repository as supabase_repos
from composition import cache
from ui import auth
from ui import cache as ui_cache
from use_cases import bank_one_offs, initialise_workspace, reconcile_subscriptions

if TYPE_CHECKING:
    import st_supabase_connection


def _get_connection() -> "st_supabase_connection.SupabaseConnection":
    """Return the shared Supabase connection for this Streamlit session."""
    return ui_cache.get_connection()


def reconcile_subscriptions_use_case() -> (
    reconcile_subscriptions.ReconcileSubscriptionsUseCase
):
    """Build ReconcileSubscriptionsUseCase wired to Supabase repositories."""
    conn = _get_connection()
    user_id = auth.get_current_user()
    cache_gateway = cache.make_cache_gateway(conn)
    return reconcile_subscriptions.ReconcileSubscriptionsUseCase(
        subscription_repo=supabase_repos.SupabaseSubscriptionRepository(
            conn,
            user_id,
            cache=cache_gateway,
        ),
        payment_repo=supabase_repos.SupabasePaymentRepository(
            conn,
            user_id,
            cache=cache_gateway,
        ),
    )


def workspace_init_use_case() -> initialise_workspace.InitialiseUserWorkspaceUseCase:
    """Build InitializeUserWorkspaceUseCase wired to Supabase repositories."""
    conn = _get_connection()
    current_user = auth.get_current_user()
    cache_gateway = cache.make_cache_gateway(conn)
    return initialise_workspace.InitialiseUserWorkspaceUseCase(
        user_id=current_user,
        budget_tracker_repo=supabase_repos.SupabaseBudgetTrackerRepository(
            connection=conn,
            user_id=current_user,
            cache=cache_gateway,
        ),
        expense_source_repo=supabase_repos.SupabaseExpenseSourceRepository(
            connection=conn,
            user_id=current_user,
            cache=cache_gateway,
        ),
    )


def bank_one_offs_use_case() -> bank_one_offs.BankOneOffsUseCase:
    """Build BankOneOffsUseCase wired to Supabase repositories."""
    conn = _get_connection()
    current_user = auth.get_current_user()
    cache_gateway = cache.make_cache_gateway(conn)
    return bank_one_offs.BankOneOffsUseCase(
        one_off_repo=supabase_repos.SupabaseOneOffRepository(
            connection=conn,
            user_id=current_user,
            cache=cache_gateway,
        ),
        budget_tracker_repo=supabase_repos.SupabaseBudgetTrackerRepository(
            connection=conn,
            user_id=current_user,
            cache=cache_gateway,
        ),
        expense_source_repo=supabase_repos.SupabaseExpenseSourceRepository(
            connection=conn,
            user_id=current_user,
            cache=cache_gateway,
        ),
        payment_repo=supabase_repos.SupabasePaymentRepository(
            connection=conn,
            user_id=current_user,
            cache=cache_gateway,
        ),
    )
