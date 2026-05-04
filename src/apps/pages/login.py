"""Stub login page for the finance tracker application."""

import streamlit as st

from libs import auth

st.title(":material/lock: Login")

user = auth.get_current_user()

st.success(f"Logged in as **{user.first_name} {user.last_name}**")
st.caption("Authentication is currently stubbed with a hardcoded user.")
