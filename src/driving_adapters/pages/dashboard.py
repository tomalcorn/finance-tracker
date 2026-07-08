"""Dashboard page for the finance tracker application."""

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

one_offs_container = st.container(border=True)
budget_tracker_container = st.container(border=True)
payments_container = st.container(border=True)
bank_accounts_container = st.container(border=True)
subscriptions_container = st.container(border=True)

bank_accounts_block.commit()
payments_block.commit()
budget_tracker_block.commit()
one_offs_block.commit()
subscriptions_block.commit()

try:
    wiring.reconcile_subscriptions_use_case().execute()
except use_case_errors.ReconciliationError:
    st.error("Error while reconciling subscriptions. Please contact support.")
    logger.exception("Subscription reconciliation failed.")
    st.stop()


with one_offs_container:
    st.subheader(":material/bubble_chart: :violet[One-Offs]")
    one_offs_block.render()

with budget_tracker_container:
    st.subheader(":material/pie_chart: :red[Budget Tracker]")
    budget_tracker_block.render()

with payments_container:
    st.subheader(":material/payments: :green[Payments]")
    payments_block.render()

with bank_accounts_container:
    st.subheader(":material/account_balance: :orange[Bank Accounts]")
    bank_accounts_block.render()

with subscriptions_container:
    st.subheader(":material/autorenew: :blue[Subscriptions]")
    subscriptions_block.render()
