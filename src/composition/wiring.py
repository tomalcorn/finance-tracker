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
    log_quick_payment,
    manage_user_settings,
    reconcile_subscriptions,
    summarise_finances,
)

if TYPE_CHECKING:
    import uuid

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


def category_data_source(
    ownership: entities.OwnershipType = entities.OwnershipType.PERSONAL,
) -> "data_source_mod.GridDataSource":
    """GridDataSource for every categories DFE.

    One source for all of them: the budget tracker grid, the subcategories grid
    and the one-offs grid are three views of one table, told apart by
    ``parent_id`` and ``accrual`` rather than by which repository they came from.
    """
    return supabase_repos.category_repository(*_repo_deps(), ownership)


def income_source_data_source(
    ownership: entities.OwnershipType = entities.OwnershipType.PERSONAL,
) -> "data_source_mod.GridDataSource":
    """GridDataSource for the income sources DFE."""
    return supabase_repos.income_source_repository(*_repo_deps(), ownership)


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


def quick_button_repository(
    ownership: entities.OwnershipType = entities.OwnershipType.PERSONAL,
) -> "repository.Repository[entities.QuickButtonModel]":
    """Repository for the current user's quick-entry buttons.

    Handed to the UI as the plain ``Repository`` port rather than a
    ``GridDataSource``: the quick-expenses page renders tiles, not a grid, and
    manages its buttons through the same read / build / save / delete surface
    every other aggregate is written with.
    """
    return supabase_repos.quick_button_repository(*_repo_deps(), ownership)


def user_settings_repository(
    ownership: entities.OwnershipType = entities.OwnershipType.PERSONAL,
) -> "repository.Repository[entities.UserSettingsModel]":
    """Repository for the preferences of one half of the user's finances."""
    return supabase_repos.user_settings_repository(*_repo_deps(), ownership)


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


def category_id_name_map(
    ownership: entities.OwnershipType = entities.OwnershipType.PERSONAL,
) -> dict[str, str]:
    """Return an ``{id: name}`` map of the categories a payment can be booked to.

    Flat for now, roots and children alike. #251 prefixes each child with its
    parent so the two levels can be told apart in the picker.
    """
    repo = supabase_repos.category_repository(
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


def joint_category_id() -> "uuid.UUID | None":
    """Return the id of the personal "Joint" root category, if it exists.

    The anchor every contribution's personal leg is booked against, so a
    contribution's ``category_id`` is derived from it rather than chosen. Reads
    the same cached personal slice :func:`category_id_name_map` does, so it
    costs no extra fetch.
    """
    repo = supabase_repos.category_repository(
        *_repo_deps(),
        entities.OwnershipType.PERSONAL,
    )
    return next(
        (
            category.id
            for category in repo.get_all()
            if category.is_root and category.name == entities.BudgetTrackerName.JOINT
        ),
        None,
    )


def budget_tracker_id_name_map(
    ownership: entities.OwnershipType = entities.OwnershipType.PERSONAL,
) -> dict[str, str]:
    """Return an ``{id: name}`` map of the current user's root categories."""
    repo = supabase_repos.category_repository(
        *_repo_deps(),
        ownership,
    )
    return {
        str(model.id): str(model.name) for model in repo.get_all() if model.is_root
    }


def reconcile_subscriptions_use_case(
    ownership: entities.OwnershipType = entities.OwnershipType.PERSONAL,
) -> reconcile_subscriptions.ReconcileSubscriptionsUseCase:
    """Build ReconcileSubscriptionsUseCase wired to Supabase repositories.

    The joint payments repository is handed over only in ``PERSONAL`` mode: a
    joint contribution is a personal standing order, so the joint instance must
    not be able to book one. It is built unconditionally for that mode — the
    repository resolves its account lazily, and a user with no joint account can
    have no contribution subscription for it to write.
    """
    deps = _repo_deps()
    joint_payment_repo = (
        supabase_repos.payment_repository(*deps, entities.OwnershipType.JOINT)
        if ownership is entities.OwnershipType.PERSONAL
        else None
    )
    return reconcile_subscriptions.ReconcileSubscriptionsUseCase(
        subscription_repo=supabase_repos.subscription_repository(
            *deps,
            ownership,
        ),
        payment_repo=supabase_repos.payment_repository(
            *deps,
            ownership,
        ),
        joint_payment_repo=joint_payment_repo,
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
        settings_repo=supabase_repos.user_settings_repository(
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
    handed in so the use case can resolve the id it stamps. Run once per session
    from the app entry point alongside the personal workspace init; it no-ops for
    a user who belongs to no joint account. Idempotent, so re-running each
    session only fills in anything missing.
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
        settings_repo=supabase_repos.user_settings_repository(
            *deps,
            entities.OwnershipType.JOINT,
        ),
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


def summarise_finances_use_case(
    ownership: entities.OwnershipType = entities.OwnershipType.PERSONAL,
) -> summarise_finances.SummariseFinancesUseCase:
    """Build SummariseFinancesUseCase wired to Supabase repositories.

    The repositories satisfy the ``ViewSource`` read port directly, and each
    resolves a cache key the page's grids already populate, so the summary
    costs no extra fetches.
    """
    deps = _repo_deps()
    return summarise_finances.SummariseFinancesUseCase(
        bank_account_source=supabase_repos.bank_account_repository(*deps, ownership),
        budget_tracker_source=supabase_repos.budget_tracker_repository(
            *deps,
            ownership,
        ),
        payment_source=supabase_repos.payment_repository(*deps, ownership),
    )


def log_quick_payment_use_case(
    ownership: entities.OwnershipType = entities.OwnershipType.PERSONAL,
) -> log_quick_payment.LogQuickPaymentUseCase:
    """Build LogQuickPaymentUseCase wired to Supabase repositories.

    Both repositories are built in the same ownership mode, so a tap on the
    joint half of the page writes a joint payment and a tap on the personal half
    a personal one.
    """
    deps = _repo_deps()
    return log_quick_payment.LogQuickPaymentUseCase(
        quick_button_repo=supabase_repos.quick_button_repository(*deps, ownership),
        payment_repo=supabase_repos.payment_repository(*deps, ownership),
    )


def manage_user_settings_use_case(
    ownership: entities.OwnershipType = entities.OwnershipType.PERSONAL,
) -> manage_user_settings.ManageUserSettingsUseCase:
    """Build ManageUserSettingsUseCase for one half's preferences.

    The ownership argument is the whole of what separates the personal and
    joint settings: the settings page builds one of these per half and each
    reads and writes only its own row.
    """
    return manage_user_settings.ManageUserSettingsUseCase(
        settings_repo=supabase_repos.user_settings_repository(
            *_repo_deps(),
            ownership,
        ),
    )


def income_roll_up_period(
    ownership: entities.OwnershipType = entities.OwnershipType.PERSONAL,
) -> entities.IncomeRollUpPeriod:
    """Return the month income sources roll up over in this half.

    The dashboards need it only to label the income column, so this hands back
    the one setting rather than the whole row. It reads through the same cache
    entry the settings page fills, so it costs no extra fetch after the first.
    """
    return manage_user_settings_use_case(ownership).load().income_roll_up_period


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
