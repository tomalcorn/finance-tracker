"""Main entry point."""

import streamlit as st

from apps.pages import constants
from libs import auth

st.set_page_config(layout="wide")

if auth.is_logged_in():
    pages = st.navigation(
        [constants.Pages.DASHBOARD.value, constants.Pages.LOGIN.value],
        position="top",
    )
else:
    pages = st.navigation([constants.Pages.LOGIN.value], position="top")
pages.run()
