"""Main entry point."""

import streamlit as st

from apps.blocks import (
    bank_accounts_block,
    budget_tracker_block,
    one_offs_block,
    payments_block,
    subscriptions_block,
)
from libs import subscription_reconciler

st.set_page_config(layout="wide")


def _dashboard() -> None:
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

    subscription_reconciler.SubscriptionReconciler().reconcile()

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


pages = st.navigation(
    [
        st.Page(_dashboard, title="Dashboard", icon=":material/dashboard:"),
        st.Page("apps/pages/login.py", title="Login", icon=":material/lock:"),
    ],
    position="top",
)
pages.run()
