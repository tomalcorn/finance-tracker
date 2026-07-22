"""Constants for Streamlit page paths."""

import enum

import streamlit as st


class Pages(enum.Enum):
    """File paths for each page in the application."""

    PERSONAL = st.Page(
        "driving_adapters/pages/personal.py",
        title="Personal",
        icon=":material/person:",
    )
    JOINT = st.Page(
        "driving_adapters/pages/joint.py",
        title="Joint",
        icon=":material/group:",
    )
    LOGIN = st.Page(
        "driving_adapters/pages/login.py",
        title="Login",
        icon=":material/lock:",
    )
