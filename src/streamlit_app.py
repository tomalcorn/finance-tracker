"""Main entry point."""

import streamlit as st

from apps.pages import constants
from libs import auth, ss_keys

st.set_page_config(layout="wide")

if not st.user.is_logged_in:
    st.session_state[ss_keys.SSKeys.FIRST_PASS] = True
    st.login("auth0")
    st.stop()

if st.session_state[ss_keys.SSKeys.FIRST_PASS]:
    current_user = auth.get_current_user()
    auth.authenticate_supabase(current_user)
    auth.seed_default_budget_trackers(current_user)
    st.session_state[ss_keys.SSKeys.FIRST_PASS] = False

pages = st.navigation(
    [constants.Pages.DASHBOARD.value, constants.Pages.LOGIN.value],
    position="top",
)
pages.run()
