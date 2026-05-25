"""Profile / login page for the finance tracker application."""

import streamlit as st

from libs import auth

st.title(":material/lock: Profile")

if auth.is_logged_in():
    user = auth.get_current_user()
    st.success(f"Logged in as **{user.first_name} {user.last_name}**")
    st.write(f"Email: {st.user.email}")
    if st.button("Log out"):
        auth.logout()
else:
    st.info("You are not logged in.")
    st.button("Log in", on_click=st.login, args=["auth0"])
