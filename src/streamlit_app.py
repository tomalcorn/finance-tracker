"""Main entry point."""

import streamlit as st

from apps.pages import constants
from libs import auth

st.set_page_config(layout="wide")

if not st.user.is_logged_in:
    st.button("Log in", on_click=st.login, args=["auth0"])
    st.stop()

auth.get_current_user()

pages = st.navigation(
    [constants.Pages.DASHBOARD.value, constants.Pages.LOGIN.value],
    position="top",
)
pages.run()
