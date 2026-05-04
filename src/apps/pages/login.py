"""Stub login page for the finance tracker application."""

import streamlit as st

from apps.pages import constants
from libs import auth

st.title(":material/lock: Login")

if auth.is_logged_in():
    user = auth.get_current_user()
    st.success(f"Logged in as **{user.first_name} {user.last_name}**")
elif st.button("Log in"):
    auth.get_current_user()
    st.switch_page(constants.Pages.DASHBOARD.value)
