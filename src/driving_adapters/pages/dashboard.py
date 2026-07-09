"""Dashboard page for the finance tracker application.

This page is the dashboard's composition root: it builds every dependency the
blocks need once, from ``composition.wiring``, and passes them into each
block's ``commit`` / ``render``. The blocks themselves no longer import
``wiring`` — they receive their grid data sources, id→name maps, and use cases
as arguments.
"""

import logging

import streamlit as st

from composition import wiring
from driving_adapters.blocks import (
    bank_accounts_block,
    budget_tracker_block,
    one_offs_block,
    payments_block,
    subscriptions_block,
)
from use_cases import errors as use_case_errors

logger = logging.getLogger(__name__)

# --- Dependencies -----------------------------------------------------------
# Grid data sources, one per aggregate grid.
bank_account_data_source = wiring.bank_account_data_source()
budget_tracker_data_source = wiring.budget_tracker_data_source()
expense_source_data_source = wiring.expense_source_data_source()
income_source_data_source = wiring.income_source_data_source()
one_off_data_source = wiring.one_off_data_source()
payment_data_source = wiring.payment_data_source()
subscription_data_source = wiring.subscription_data_source()

# Foreign-key id→name maps, shared across the blocks that display them.
bank_account_map = wiring.bank_account_id_name_map()
expense_source_map = wiring.expense_source_id_name_map()
income_source_map = wiring.income_source_id_name_map()
budget_tracker_map = wiring.budget_tracker_id_name_map()

# Use cases.
bank_one_offs_use_case = wiring.bank_one_offs_use_case()

one_offs_container = st.container(border=True)
budget_tracker_container = st.container(border=True)
payments_container = st.container(border=True)
bank_accounts_container = st.container(border=True)
subscriptions_container = st.container(border=True)

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

try:
    wiring.reconcile_subscriptions_use_case().execute()
except use_case_errors.ReconciliationError:
    st.error("Error while reconciling subscriptions. Please contact support.")
    logger.exception("Subscription reconciliation failed.")
    st.stop()

# Read after reconciliation so computed balances reflect any payments it created.
bank_accounts = wiring.bank_account_views()


with one_offs_container:
    st.subheader(":material/bubble_chart: :violet[One-Offs]")
    one_offs_block.render(
        one_off_data_source,
        budget_tracker_map,
        bank_account_map,
        bank_one_offs_use_case,
    )

with budget_tracker_container:
    st.subheader(":material/pie_chart: :red[Budget Tracker]")
    budget_tracker_block.render(
        budget_tracker_data_source,
        expense_source_data_source,
        income_source_data_source,
        budget_tracker_map,
    )

with payments_container:
    st.subheader(":material/payments: :green[Payments]")
    payments_block.render(
        payment_data_source,
        bank_account_map,
        expense_source_map,
        income_source_map,
    )

with bank_accounts_container:
    st.subheader(":material/account_balance: :orange[Bank Accounts]")
    bank_accounts_block.render(bank_account_data_source, bank_accounts)

with subscriptions_container:
    st.subheader(":material/autorenew: :blue[Subscriptions]")
    subscriptions_block.render(
        subscription_data_source,
        bank_account_map,
        expense_source_map,
    )
