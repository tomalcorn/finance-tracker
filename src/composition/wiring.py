"""Construct use cases and grid data sources with live dependencies."""

from typing import TYPE_CHECKING

from composition import cache
from driven_adapters.supabase import repository as supabase_repos
from driving_adapters import auth
from driving_adapters import cache as ui_cache
from use_cases import bank_one_offs, initialise_workspace, reconcile_subscriptions

if TYPE_CHECKING:
    import st_supabase_connection

    from domain import read_models
    from driving_adapters.components.dfes import data_source as data_source_mod


def _get_connection() -> "st_supabase_connection.SupabaseConnection":
    """Return the shared Supabase connection for this Streamlit session."""
    return ui_cache.get_connection()


def _user_and_cache() -> tuple[str, cache.StreamlitCacheGateway]:
    """Return the (user_id, cache) pair every repository factory needs."""
    conn = _get_connection()
    return auth.get_current_user(), cache.make_cache_gateway(conn)


def bank_account_data_source() -> "data_source_mod.GridDataSource":
    """GridDataSource for the bank accounts DFE."""
    return supabase_repos.bank_account_repository(*_user_and_cache())


def budget_tracker_data_source() -> "data_source_mod.GridDataSource":
    """GridDataSource for the budget tracker DFE."""
    return supabase_repos.budget_tracker_repository(*_user_and_cache())


def expense_source_data_source() -> "data_source_mod.GridDataSource":
    """GridDataSource for the expense sources DFE."""
    return supabase_repos.expense_source_repository(*_user_and_cache())


def income_source_data_source() -> "data_source_mod.GridDataSource":
    """GridDataSource for the income sources DFE."""
    return supabase_repos.income_source_repository(*_user_and_cache())


def one_off_data_source() -> "data_source_mod.GridDataSource":
    """GridDataSource for the one-offs DFE."""
    return supabase_repos.one_off_repository(*_user_and_cache())


def payment_data_source() -> "data_source_mod.GridDataSource":
    """GridDataSource for the payments DFEs."""
    return supabase_repos.payment_repository(*_user_and_cache())


def subscription_data_source() -> "data_source_mod.GridDataSource":
    """GridDataSource for the subscriptions DFE."""
    return supabase_repos.subscription_repository(*_user_and_cache())


def bank_account_views() -> "list[read_models.BankAccountView]":
    """Return the current user's bank accounts as typed view rows.

    Carries the computed ``current_balance`` column, so it is the read the
    bank-accounts overview metrics use.
    """
    repo = supabase_repos.bank_account_repository(*_user_and_cache())
    return repo.rows()


def bank_account_id_name_map() -> dict[str, str]:
    """Return an ``{id: name}`` map of the current user's bank accounts."""
    repo = supabase_repos.bank_account_repository(*_user_and_cache())
    return {str(model.id): str(model.name) for model in repo.get_all()}


def expense_source_id_name_map() -> dict[str, str]:
    """Return an ``{id: name}`` map of the current user's expense sources."""
    repo = supabase_repos.expense_source_repository(*_user_and_cache())
    return {str(model.id): str(model.name) for model in repo.get_all()}


def income_source_id_name_map() -> dict[str, str]:
    """Return an ``{id: name}`` map of the current user's income sources."""
    repo = supabase_repos.income_source_repository(*_user_and_cache())
    return {str(model.id): str(model.name) for model in repo.get_all()}


def budget_tracker_id_name_map() -> dict[str, str]:
    """Return an ``{id: name}`` map of the current user's budget tracker items."""
    repo = supabase_repos.budget_tracker_repository(*_user_and_cache())
    return {str(model.id): str(model.name) for model in repo.get_all()}


def reconcile_subscriptions_use_case() -> (
    reconcile_subscriptions.ReconcileSubscriptionsUseCase
):
    """Build ReconcileSubscriptionsUseCase wired to Supabase repositories."""
    user_id, cache_gateway = _user_and_cache()
    return reconcile_subscriptions.ReconcileSubscriptionsUseCase(
        subscription_repo=supabase_repos.subscription_repository(
            user_id,
            cache_gateway,
        ),
        payment_repo=supabase_repos.payment_repository(user_id, cache_gateway),
    )


def workspace_init_use_case() -> initialise_workspace.InitialiseUserWorkspaceUseCase:
    """Build InitializeUserWorkspaceUseCase wired to Supabase repositories."""
    user_id, cache_gateway = _user_and_cache()
    return initialise_workspace.InitialiseUserWorkspaceUseCase(
        user_id=user_id,
        budget_tracker_repo=supabase_repos.budget_tracker_repository(
            user_id,
            cache_gateway,
        ),
        expense_source_repo=supabase_repos.expense_source_repository(
            user_id,
            cache_gateway,
        ),
    )


def bank_one_offs_use_case() -> bank_one_offs.BankOneOffsUseCase:
    """Build BankOneOffsUseCase wired to Supabase repositories."""
    user_id, cache_gateway = _user_and_cache()
    return bank_one_offs.BankOneOffsUseCase(
        one_off_repo=supabase_repos.one_off_repository(user_id, cache_gateway),
        budget_tracker_repo=supabase_repos.budget_tracker_repository(
            user_id,
            cache_gateway,
        ),
        expense_source_repo=supabase_repos.expense_source_repository(
            user_id,
            cache_gateway,
        ),
        payment_repo=supabase_repos.payment_repository(user_id, cache_gateway),
    )
