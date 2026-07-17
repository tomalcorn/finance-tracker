"""Constants for Streamlit page paths."""

import enum

import streamlit as st


class Pages(enum.Enum):
    """File paths for each page in the application."""

    DASHBOARD = st.Page(
        "driving_adapters/pages/dashboard.py",
        title="Dashboard",
        icon=":material/dashboard:",
    )
    LOGIN = st.Page(
        "driving_adapters/pages/login.py",
        title="Login",
        icon=":material/lock:",
    )
    JOINT_DEMO = st.Page(
        "driving_adapters/pages/joint_demo.py",
        title="Joint RLS demo",
        icon=":material/group:",
    )
