"""Main entry point."""

import streamlit as st

from apps.blocks import bank_accounts_block, budget_tracker_block, payments_block

payments_container = st.container()
bank_accounts_container = st.container()
budget_tracker_container = st.container()

bank_accounts_block.commit()
payments_block.commit()
budget_tracker_block.commit()

with bank_accounts_container:
    bank_accounts_block.render()

with payments_container:
    payments_block.render()

with budget_tracker_container:
    budget_tracker_block.render()
