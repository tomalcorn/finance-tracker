"""Factory functions for constructing use cases with live dependencies."""

import st_supabase_connection
import streamlit as st

from adapters.supabase import repository as supabase_repos
from ui import auth, data_client
from use_cases import bank_one_offs, initialise_workspace, reconcile_subscriptions


def get_connection() -> st_supabase_connection.SupabaseConnection:
    """Return the shared Supabase connection for this Streamlit session."""
    return st.connection("supabase", type=st_supabase_connection.SupabaseConnection)


def reconcile_subscriptions_use_case() -> (
    reconcile_subscriptions.ReconcileSubscriptionsUseCase
):
    """Build ReconcileSubscriptionsUseCase wired to Supabase repositories."""
    conn = get_connection()
    user_id = auth.get_current_user()
    fetch_rows = data_client.make_repo_fetch_fn(conn)
    return reconcile_subscriptions.ReconcileSubscriptionsUseCase(
        subscription_repo=supabase_repos.SupabaseSubscriptionRepository(
            conn, user_id, fetch_rows=fetch_rows,
        ),
        payment_repo=supabase_repos.SupabasePaymentRepository(
            conn, user_id, fetch_rows=fetch_rows,
        ),
    )


def workspace_init_use_case() -> initialise_workspace.InitialiseUserWorkspaceUseCase:
    """Build InitializeUserWorkspaceUseCase wired to Supabase repositories."""
    conn = get_connection()
    current_user = auth.get_current_user()
    fetch_rows = data_client.make_repo_fetch_fn(conn)
    return initialise_workspace.InitialiseUserWorkspaceUseCase(
        user_id=current_user,
        budget_tracker_repo=supabase_repos.SupabaseBudgetTrackerRepository(
            connection=conn,
            user_id=current_user,
            fetch_rows=fetch_rows,
        ),
        expense_source_repo=supabase_repos.SupabaseExpenseSourceRepository(
            connection=conn,
            user_id=current_user,
            fetch_rows=fetch_rows,
        ),
    )


def bank_one_offs_use_case() -> bank_one_offs.BankOneOffsUseCase:
    """Build BankOneOffsUseCase wired to Supabase repositories."""
    conn = get_connection()
    current_user = auth.get_current_user()
    fetch_rows = data_client.make_repo_fetch_fn(conn)
    return bank_one_offs.BankOneOffsUseCase(
        one_off_repo=supabase_repos.SupabaseOneOffRepository(
            connection=conn,
            user_id=current_user,
            fetch_rows=fetch_rows,
        ),
        budget_tracker_repo=supabase_repos.SupabaseBudgetTrackerRepository(
            connection=conn,
            user_id=current_user,
            fetch_rows=fetch_rows,
        ),
        expense_source_repo=supabase_repos.SupabaseExpenseSourceRepository(
            connection=conn,
            user_id=current_user,
            fetch_rows=fetch_rows,
        ),
        payment_repo=supabase_repos.SupabasePaymentRepository(
            connection=conn,
            user_id=current_user,
            fetch_rows=fetch_rows,
        ),
    )
