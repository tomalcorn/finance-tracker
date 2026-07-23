"""Construct use cases and grid data sources with live dependencies."""

from typing import TYPE_CHECKING

import st_supabase_connection
import streamlit as st

from domain import entities
from driven_adapters.supabase import authenticator as supabase_auth
from driven_adapters.supabase import repository as supabase_repos
from driving_adapters import auth
from driving_adapters import cache as ui_cache
from use_cases import (
    bank_one_offs,
    contribute_to_joint,
    initialise_joint_workspace,
    initialise_workspace,
    reconcile_subscriptions,
)

if TYPE_CHECKING:
    from domain import read_models
    from driving_adapters.components.dfes import data_source as data_source_mod
    from ports import authentication, repository


def _connection() -> st_supabase_connection.SupabaseConnection:
    """Return the shared Supabase connection for this session."""
    return st.connection("supabase", type=st_supabase_connection.SupabaseConnection)


def authenticator() -> "authentication.Authenticator":
    """Build the Supabase authenticator with the shared connection and secret."""
    jwt_secret = str(st.secrets["supabase_admin"]["jwt_secret"])
    return supabase_auth.SupabaseAuthenticator(_connection(), jwt_secret)


def _repo_deps() -> tuple[
    str,
    ui_cache.StreamlitCache,
    st_supabase_connection.SupabaseConnection,
]:
    """Return the (user_id, cache, connection) triple every repo factory needs.

    Ownership-scoped repos discover the user's joint accounts themselves, so no
    joint-account ids are threaded through here.
    """
    return auth.get_current_user(), ui_cache.StreamlitCache(), _connection()


def bank_account_data_source(
    ownership: entities.OwnershipType = entities.OwnershipType.PERSONAL,
) -> "data_source_mod.GridDataSource":
    """GridDataSource for the bank accounts DFE."""
    return supabase_repos.bank_account_repository(*_repo_deps(), ownership)


def budget_tracker_data_source(
    ownership: entities.OwnershipType = entities.OwnershipType.PERSONAL,
) -> "data_source_mod.GridDataSource":
    """GridDataSource for the budget tracker DFE."""
    return supabase_repos.budget_tracker_repository(*_repo_deps(), ownership)


def expense_source_data_source(
    ownership: entities.OwnershipType = entities.OwnershipType.PERSONAL,
) -> "data_source_mod.GridDataSource":
    """GridDataSource for the expense sources DFE."""
    return supabase_repos.expense_source_repository(*_repo_deps(), ownership)


def income_source_data_source(
    ownership: entities.OwnershipType = entities.OwnershipType.PERSONAL,
) -> "data_source_mod.GridDataSource":
    """GridDataSource for the income sources DFE."""
    return supabase_repos.income_source_repository(*_repo_deps(), ownership)


def one_off_data_source(
    ownership: entities.OwnershipType = entities.OwnershipType.PERSONAL,
) -> "data_source_mod.GridDataSource":
    """GridDataSource for the one-offs DFE."""
    return supabase_repos.one_off_repository(*_repo_deps(), ownership)


def payment_data_source(
    ownership: entities.OwnershipType = entities.OwnershipType.PERSONAL,
) -> "data_source_mod.GridDataSource":
    """GridDataSource for the payments DFEs."""
    return supabase_repos.payment_repository(*_repo_deps(), ownership)


def subscription_data_source(
    ownership: entities.OwnershipType = entities.OwnershipType.PERSONAL,
) -> "data_source_mod.GridDataSource":
    """GridDataSource for the subscriptions DFE."""
    return supabase_repos.subscription_repository(*_repo_deps(), ownership)


def joint_account_repository() -> "repository.Repository[entities.JointAccountModel]":
    """Repository for the joint accounts the current user belongs to.

    Not ownership-scoped: joint_accounts has no ownership dimension, so it reads
    under the single ``{user_id}:joint_accounts`` key — the same entry the
    ownership-scoped repos consult to discover the user's accounts.
    """
    return supabase_repos.joint_account_repository(*_repo_deps())


def joint_account_member_repository() -> (
    "repository.Repository[entities.JointAccountMemberModel]"
):
    """Repository for the current user's joint-account memberships."""
    return supabase_repos.joint_account_member_repository(*_repo_deps())


def bank_account_views(
    ownership: entities.OwnershipType = entities.OwnershipType.PERSONAL,
) -> "list[read_models.BankAccountView]":
    """Return the current user's bank accounts as typed view rows.

    Carries the computed ``current_balance`` column, so it is the read the
    bank-accounts overview metrics use.
    """
    repo = supabase_repos.bank_account_repository(
        *_repo_deps(),
        ownership,
    )
    return repo.rows()


def bank_account_id_name_map(
    ownership: entities.OwnershipType = entities.OwnershipType.PERSONAL,
) -> dict[str, str]:
    """Return an ``{id: name}`` map of the current user's bank accounts."""
    repo = supabase_repos.bank_account_repository(
        *_repo_deps(),
        ownership,
    )
    return {str(model.id): str(model.name) for model in repo.get_all()}


def expense_source_id_name_map(
    ownership: entities.OwnershipType = entities.OwnershipType.PERSONAL,
) -> dict[str, str]:
    """Return an ``{id: name}`` map of the current user's expense sources."""
    repo = supabase_repos.expense_source_repository(
        *_repo_deps(),
        ownership,
    )
    return {str(model.id): str(model.name) for model in repo.get_all()}


def income_source_id_name_map(
    ownership: entities.OwnershipType = entities.OwnershipType.PERSONAL,
) -> dict[str, str]:
    """Return an ``{id: name}`` map of the current user's income sources."""
    repo = supabase_repos.income_source_repository(
        *_repo_deps(),
        ownership,
    )
    return {str(model.id): str(model.name) for model in repo.get_all()}


def budget_tracker_id_name_map(
    ownership: entities.OwnershipType = entities.OwnershipType.PERSONAL,
) -> dict[str, str]:
    """Return an ``{id: name}`` map of the current user's budget tracker items."""
    repo = supabase_repos.budget_tracker_repository(
        *_repo_deps(),
        ownership,
    )
    return {str(model.id): str(model.name) for model in repo.get_all()}


def reconcile_subscriptions_use_case(
    ownership: entities.OwnershipType = entities.OwnershipType.PERSONAL,
) -> reconcile_subscriptions.ReconcileSubscriptionsUseCase:
    """Build ReconcileSubscriptionsUseCase wired to Supabase repositories."""
    deps = _repo_deps()
    return reconcile_subscriptions.ReconcileSubscriptionsUseCase(
        subscription_repo=supabase_repos.subscription_repository(
            *deps,
            ownership,
        ),
        payment_repo=supabase_repos.payment_repository(
            *deps,
            ownership,
        ),
    )


def workspace_init_use_case() -> initialise_workspace.InitialiseUserWorkspaceUseCase:
    """Build InitialiseUserWorkspaceUseCase wired to Supabase repositories.

    Personal-only on purpose: seeding a joint account is not the same job as
    seeding a personal workspace (a joint account should not simply inherit
    the personal budget trackers), so it needs its own use case rather than an
    ownership argument here.
    """
    deps = _repo_deps()
    user_id = deps[0]
    return initialise_workspace.InitialiseUserWorkspaceUseCase(
        user_id=user_id,
        budget_tracker_repo=supabase_repos.budget_tracker_repository(
            *deps,
            entities.OwnershipType.PERSONAL,
        ),
        expense_source_repo=supabase_repos.expense_source_repository(
            *deps,
            entities.OwnershipType.PERSONAL,
        ),
    )


def joint_workspace_init_use_case() -> (
    initialise_joint_workspace.InitialiseJointWorkspaceUseCase
):
    """Build InitialiseJointWorkspaceUseCase wired to Supabase repositories.

    The counterpart to :func:`workspace_init_use_case` for a joint account: the
    trackers/sources repos are built in ``JOINT`` mode so every row is stamped
    ``ownership_type='joint'`` and account-scoped, and a joint-accounts repo is
    handed in so the use case can resolve the id it stamps. Deliberately has no
    wired call site: a joint account is seeded once when it is created, and
    in-app joint-account creation is deferred (#177), so accounts are created and
    seeded manually for now. When creation lands, its flow calls this.
    """
    deps = _repo_deps()
    user_id = deps[0]
    return initialise_joint_workspace.InitialiseJointWorkspaceUseCase(
        user_id=user_id,
        budget_tracker_repo=supabase_repos.budget_tracker_repository(
            *deps,
            entities.OwnershipType.JOINT,
        ),
        expense_source_repo=supabase_repos.expense_source_repository(
            *deps,
            entities.OwnershipType.JOINT,
        ),
        joint_account_repo=supabase_repos.joint_account_repository(*deps),
    )


def contribute_to_joint_use_case() -> contribute_to_joint.ContributeToJointUseCase:
    """Build ContributeToJointUseCase wired to Supabase repositories.

    Takes no ownership argument: a contribution spans both halves by
    definition, so it is handed one payments repository per mode. The expense
    sources are personal because the "Joint" source it books against is the
    personal-side anchor for the transfer.
    """
    deps = _repo_deps()
    user_id = deps[0]
    return contribute_to_joint.ContributeToJointUseCase(
        user_id=user_id,
        personal_payment_repo=supabase_repos.payment_repository(
            *deps,
            entities.OwnershipType.PERSONAL,
        ),
        joint_payment_repo=supabase_repos.payment_repository(
            *deps,
            entities.OwnershipType.JOINT,
        ),
        expense_source_repo=supabase_repos.expense_source_repository(
            *deps,
            entities.OwnershipType.PERSONAL,
        ),
        joint_account_repo=supabase_repos.joint_account_repository(*deps),
    )


def bank_one_offs_use_case(
    ownership: entities.OwnershipType = entities.OwnershipType.PERSONAL,
) -> bank_one_offs.BankOneOffsUseCase:
    """Build BankOneOffsUseCase wired to Supabase repositories."""
    deps = _repo_deps()
    return bank_one_offs.BankOneOffsUseCase(
        one_off_repo=supabase_repos.one_off_repository(
            *deps,
            ownership,
        ),
        budget_tracker_repo=supabase_repos.budget_tracker_repository(
            *deps,
            ownership,
        ),
        expense_source_repo=supabase_repos.expense_source_repository(
            *deps,
            ownership,
        ),
        payment_repo=supabase_repos.payment_repository(
            *deps,
            ownership,
        ),
    )
