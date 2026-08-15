"""Quick expenses page: log a preset expense from a phone in one tap.

The composition root for the quick-entry block, in the shape ``personal.py`` and
``joint.py`` use: every dependency is built here from ``composition.wiring`` and
passed in.

Unlike the dashboards this page serves both halves of the finances from one
place — a phone in a shop is a bad moment to go looking for the right page — so
the ownership selector is read first and every dependency below it is built in
the mode it returns.
"""

import streamlit as st

from composition import wiring
from driving_adapters import error_boundary
from driving_adapters.blocks import quick_expenses_block

# Narrower than the dashboards' wide layout: this page is built for a phone.
st.set_page_config(layout="centered")

st.title(":material/bolt: Quick Expenses")
st.caption("Tap a button to log the expense it stands for.")

with error_boundary.boundary("loading your quick expenses"):
    # Also warms the ``{user_id}:joint_accounts`` cache entry a joint-scoped
    # repository consults to resolve its account, so it costs no extra fetch.
    has_joint_account = bool(wiring.joint_account_repository().get_all())
    ownership = quick_expenses_block.ownership_selector(
        has_joint_account=has_joint_account,
    )

    quick_button_repo = wiring.quick_button_repository(ownership)
    log_quick_payment_use_case = wiring.log_quick_payment_use_case(ownership)
    bank_account_map = wiring.bank_account_id_name_map(ownership)
    category_map = wiring.category_id_name_map(ownership)

with error_boundary.boundary("loading your quick buttons"):
    quick_expenses_block.render(
        quick_button_repo,
        log_quick_payment_use_case,
        bank_account_map,
        category_map,
    )
