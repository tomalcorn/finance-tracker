"""Main entry point."""

import streamlit as st

from apps.blocks import bank_accounts_block, payments_block

payments_container = st.container()
bank_accounts_container = st.container()
ba_block = bank_accounts_block.BankAccountsBlock()
payments_block_instance = payments_block.PaymentsBlock()


ba_block.commit()
payments_block_instance.commit()

with bank_accounts_container:
    ba_block.render()

with payments_container:
    payments_block_instance.render()
