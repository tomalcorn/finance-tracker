"""Joint dashboard page for the finance tracker application.

The joint counterpart of ``personal.py``: same composition-root shape, same
reused blocks, but every dependency is built with ``JOINT`` ownership, so the
grids, maps, and use cases operate on the ``ownership_type='joint'`` rows of the
account the current user belongs to. RLS already limits reads to permitted
rows; the ownership argument narrows that to the joint slice (the T5 cache-key
split).

A user belongs to at most one joint account. If they belong to none there is
nothing to show, so the page checks up front and stops with a prompt rather than
letting each joint read raise ``NoJointAccountError``.
"""

import streamlit as st

from composition import wiring
from domain import entities
from driving_adapters import error_boundary
from driving_adapters.blocks import (
    bank_accounts_block,
    budget,
    payments_block,
    subscriptions_block,
    summary_block,
)

_JOINT = entities.OwnershipType.JOINT

st.title(":material/group: Joint")

with error_boundary.boundary("loading your joint dashboard"):
    # A user belongs to at most one joint account. Reading it here both gates
    # the page and warms the ``{user_id}:joint_accounts`` cache entry every
    # joint-scoped repo consults to resolve its account, so it costs no extra
    # fetch.
    joint_accounts = wiring.joint_account_repository().get_all()
    if not joint_accounts:
        st.info(
            "You don't have a joint account yet. Once you're a member of one, "
            "your shared accounts, budget, and payments will appear here. "
            "See the [Joint Accounts guide](/joint_accounts) to learn how they "
            "work and how to set one up.",
        )
        st.stop()

    # Name the account so this page cannot be mistaken for Personal. Co-member
    # names are not shown: the membership table is own-rows-only under RLS, so a
    # member cannot read who else belongs (see #176). Surfacing them is a
    # follow-up once membership exposes co-members.
    st.caption(f":orange[Shared account] · **{joint_accounts[0].name}**")

    # Grid data sources, one per aggregate grid.
    bank_account_data_source = wiring.bank_account_data_source(_JOINT)
    # One source behind every category grid: the trackers, their
    # subcategories and any orphan are slices of the one category tree.
    category_data_source = wiring.category_data_source(_JOINT)
    budget_tracker_sources = budget.BudgetTrackerSources(
        categories=category_data_source,
        income_sources=wiring.income_source_data_source(_JOINT),
    )
    payment_data_source = wiring.payment_data_source(_JOINT)
    subscription_data_source = wiring.subscription_data_source(_JOINT)

    # Foreign-key id→name maps, shared across the blocks that display them.
    bank_account_map = wiring.bank_account_id_name_map(_JOINT)
    category_map = wiring.category_id_name_map(_JOINT)
    income_source_map = wiring.income_source_id_name_map(_JOINT)
    budget_tracker_map = wiring.budget_tracker_id_name_map(_JOINT)

    # Use cases.
    bank_one_offs_use_case = wiring.bank_one_offs_use_case(_JOINT)

    # Which month the income sources tab rolls its payments up over, from the
    # *account's* settings rather than either member's own, so both members see
    # the same figures. The view has already applied it; the block takes it only
    # to label the column.
    income_roll_up_period = wiring.income_roll_up_period(_JOINT)

    # No contribute button: contributing funds joint from personal, so it
    # belongs on the other page.
    budget_area = budget.BudgetArea(
        sources=budget_tracker_sources,
        budget_tracker_map=budget_tracker_map,
        bank_account_map=bank_account_map,
        bank_one_offs_use_case=bank_one_offs_use_case,
        income_roll_up_period=income_roll_up_period,
    )

summary_container = st.container(border=True)
budget_tracker_container = st.container(border=True)
payments_container = st.container(border=True)
bank_accounts_container = st.container(border=True)
subscriptions_container = st.container(border=True)

with error_boundary.boundary("saving your latest changes"):
    bank_accounts_block.commit(bank_account_data_source)
    payments_block.commit(
        payment_data_source,
        bank_account_map,
        category_map,
        income_source_map,
    )
    budget.commit(budget_area)
    subscriptions_block.commit(
        subscription_data_source,
        bank_account_map,
        category_map,
    )

with error_boundary.boundary("reconciling your subscriptions"):
    wiring.reconcile_subscriptions_use_case(_JOINT).execute()


with summary_container, error_boundary.boundary("loading your summary"):
    # Read after reconciliation so the figures include its new payments.
    st.subheader(":material/insights: :orange[Summary]")
    summary_block.render(wiring.summarise_finances_use_case(_JOINT).execute())

with budget_tracker_container, error_boundary.boundary("loading your budget"):
    st.subheader(":material/pie_chart: :orange[Budget]")
    budget.render(budget_area)

with payments_container, error_boundary.boundary("loading your payments"):
    st.subheader(":material/payments: :orange[Payments]")
    payments_block.render(
        payment_data_source,
        bank_account_map,
        category_map,
        income_source_map,
    )

with bank_accounts_container, error_boundary.boundary("loading your bank accounts"):
    # Read after reconciliation so computed balances reflect its new payments.
    bank_accounts = wiring.bank_account_views(_JOINT)
    st.subheader(":material/account_balance: :orange[Bank Accounts]")
    bank_accounts_block.render(bank_account_data_source, bank_accounts)

with subscriptions_container, error_boundary.boundary("loading your subscriptions"):
    st.subheader(":material/autorenew: :orange[Subscriptions]")
    subscriptions_block.render(
        subscription_data_source,
        bank_account_map,
        category_map,
    )
