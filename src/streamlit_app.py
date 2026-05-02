"""Main entry point."""

import streamlit as st

from apps.blocks import (
    bank_accounts_block,
    budget_tracker_block,
    one_offs_block,
    payments_block,
)

st.set_page_config(layout="wide")

one_offs_container = st.container(border=True)
budget_tracker_container = st.container(border=True)
payments_container = st.container(border=True)
bank_accounts_container = st.container(border=True)

bank_accounts_block.commit()
payments_block.commit()
budget_tracker_block.commit()
one_offs_block.commit()

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
