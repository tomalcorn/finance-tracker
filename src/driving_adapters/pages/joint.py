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
    budget_tracker_block,
    one_offs_block,
    payments_block,
    subscriptions_block,
)

_JOINT = entities.OwnershipType.JOINT

st.title(":material/group: Joint")
st.caption("Shared accounts, budget, and payments for your joint account.")

with error_boundary.boundary("loading your joint dashboard"):
    # A user belongs to at most one joint account. Reading it here both gates
    # the page and warms the ``{user_id}:joint_accounts`` cache entry every
    # joint-scoped repo consults to resolve its account, so it costs no extra
    # fetch.
    if not wiring.joint_account_repository().get_all():
        st.info(
            "You don't have a joint account yet. Once you're a member of one, "
            "your shared accounts, budget, and payments will appear here. "
            "See the [Joint Accounts guide](/joint_accounts) to learn how they "
            "work and how to set one up.",
        )
        st.stop()

    # Grid data sources, one per aggregate grid.
    bank_account_data_source = wiring.bank_account_data_source(_JOINT)
    budget_tracker_data_source = wiring.budget_tracker_data_source(_JOINT)
    expense_source_data_source = wiring.expense_source_data_source(_JOINT)
    income_source_data_source = wiring.income_source_data_source(_JOINT)
    one_off_data_source = wiring.one_off_data_source(_JOINT)
    payment_data_source = wiring.payment_data_source(_JOINT)
    subscription_data_source = wiring.subscription_data_source(_JOINT)

    # Foreign-key id→name maps, shared across the blocks that display them.
    bank_account_map = wiring.bank_account_id_name_map(_JOINT)
    expense_source_map = wiring.expense_source_id_name_map(_JOINT)
    income_source_map = wiring.income_source_id_name_map(_JOINT)
    budget_tracker_map = wiring.budget_tracker_id_name_map(_JOINT)

    # Use cases.
    bank_one_offs_use_case = wiring.bank_one_offs_use_case(_JOINT)

one_offs_container = st.container(border=True)
budget_tracker_container = st.container(border=True)
payments_container = st.container(border=True)
bank_accounts_container = st.container(border=True)
subscriptions_container = st.container(border=True)

with error_boundary.boundary("saving your latest changes"):
    bank_accounts_block.commit(bank_account_data_source)
    payments_block.commit(
        payment_data_source,
        bank_account_map,
        expense_source_map,
        income_source_map,
    )
    budget_tracker_block.commit(
        budget_tracker_data_source,
        expense_source_data_source,
        income_source_data_source,
        budget_tracker_map,
    )
    one_offs_block.commit(one_off_data_source, budget_tracker_map)
    subscriptions_block.commit(
        subscription_data_source,
        bank_account_map,
        expense_source_map,
    )

with error_boundary.boundary("reconciling your subscriptions"):
    wiring.reconcile_subscriptions_use_case(_JOINT).execute()


with one_offs_container, error_boundary.boundary("loading your one-offs"):
    st.subheader(":material/bubble_chart: :violet[One-Offs]")
    one_offs_block.render(
        one_off_data_source,
        budget_tracker_map,
        bank_account_map,
        bank_one_offs_use_case,
    )

with budget_tracker_container, error_boundary.boundary("loading your budget tracker"):
    st.subheader(":material/pie_chart: :red[Budget Tracker]")
    budget_tracker_block.render(
        budget_tracker_data_source,
        expense_source_data_source,
        income_source_data_source,
        budget_tracker_map,
    )

with payments_container, error_boundary.boundary("loading your payments"):
    st.subheader(":material/payments: :green[Payments]")
    payments_block.render(
        payment_data_source,
        bank_account_map,
        expense_source_map,
        income_source_map,
    )

with bank_accounts_container, error_boundary.boundary("loading your bank accounts"):
    # Read after reconciliation so computed balances reflect its new payments.
    bank_accounts = wiring.bank_account_views(_JOINT)
    st.subheader(":material/account_balance: :orange[Bank Accounts]")
    bank_accounts_block.render(bank_account_data_source, bank_accounts)

with subscriptions_container, error_boundary.boundary("loading your subscriptions"):
    st.subheader(":material/autorenew: :blue[Subscriptions]")
    subscriptions_block.render(
        subscription_data_source,
        bank_account_map,
        expense_source_map,
    )
