"""Factory functions for constructing use cases with live dependencies."""

from typing import TYPE_CHECKING

from adapters.supabase import repository as supabase_repos
from composition import cache, grid_data_source
from domain import read_models
from ui import auth
from ui import cache as ui_cache
from use_cases import bank_one_offs, initialise_workspace, reconcile_subscriptions

if TYPE_CHECKING:
    from collections.abc import Callable

    import pydantic
    import st_supabase_connection


def _get_connection() -> "st_supabase_connection.SupabaseConnection":
    """Return the shared Supabase connection for this Streamlit session."""
    return ui_cache.get_connection()


def _grid_data_source(
    repository_factory: "Callable[..., supabase_repos.SupabaseRepositoryBase]",
    view_model: "type[pydantic.BaseModel] | None" = None,
) -> grid_data_source.RepositoryGridDataSource:
    """Build a GridDataSource backed by the given repository, fully wired.

    Args:
        repository_factory: The repository class to instantiate for reads.
        view_model: The ``domain.read_models`` view model that ``rows()`` maps
            raw rows into. ``None`` for payments, which has no view.

    """
    conn = _get_connection()
    user_id = auth.get_current_user()
    cache_gateway = cache.make_cache_gateway(conn)
    return grid_data_source.RepositoryGridDataSource(
        repository_factory(conn, user_id, cache=cache_gateway),
        view_model=view_model,
    )


def bank_account_data_source() -> grid_data_source.RepositoryGridDataSource:
    """GridDataSource for the bank accounts DFE."""
    return _grid_data_source(
        supabase_repos.SupabaseBankAccountRepository,
        read_models.BankAccountView,
    )


def budget_tracker_data_source() -> grid_data_source.RepositoryGridDataSource:
    """GridDataSource for the budget tracker DFE."""
    return _grid_data_source(
        supabase_repos.SupabaseBudgetTrackerRepository,
        read_models.BudgetTrackerView,
    )


def expense_source_data_source() -> grid_data_source.RepositoryGridDataSource:
    """GridDataSource for the expense sources DFE."""
    return _grid_data_source(
        supabase_repos.SupabaseExpenseSourceRepository,
        read_models.ExpenseSourceView,
    )


def income_source_data_source() -> grid_data_source.RepositoryGridDataSource:
    """GridDataSource for the income sources DFE."""
    return _grid_data_source(
        supabase_repos.SupabaseIncomeSourceRepository,
        read_models.IncomeSourceView,
    )


def one_off_data_source() -> grid_data_source.RepositoryGridDataSource:
    """GridDataSource for the one-offs DFE."""
    return _grid_data_source(
        supabase_repos.SupabaseOneOffRepository,
        read_models.OneOffView,
    )


def payment_data_source() -> grid_data_source.RepositoryGridDataSource:
    """GridDataSource for the payments DFEs (no view model; rows() unavailable)."""
    return _grid_data_source(supabase_repos.SupabasePaymentRepository)


def subscription_data_source() -> grid_data_source.RepositoryGridDataSource:
    """GridDataSource for the subscriptions DFE."""
    return _grid_data_source(
        supabase_repos.SupabaseSubscriptionRepository,
        read_models.SubscriptionView,
    )


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
