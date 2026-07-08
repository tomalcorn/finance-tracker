"""Constants for Streamlit page paths."""

import enum

import streamlit as st


class Pages(enum.Enum):
    """File paths for each page in the application."""

    DASHBOARD = st.Page(
        "ui/pages/dashboard.py",
        title="Dashboard",
        icon=":material/dashboard:",
    )
    LOGIN = st.Page("ui/pages/login.py", title="Login", icon=":material/lock:")
