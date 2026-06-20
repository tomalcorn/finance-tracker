"""Profile / login page for the finance tracker application."""

import streamlit as st

from ui import auth

st.title(":material/lock: Profile")

if auth.is_logged_in():
    st.write(f"Logged in as **{st.user.email}**")
    if st.button("Log out"):
        auth.logout()
        st.rerun()
else:
    st.login("auth0")
    st.stop()
