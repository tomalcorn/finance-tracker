"""Constants for Streamlit page paths."""

import enum

import streamlit as st


class PagePaths(enum.StrEnum):
    """The URL pathname each application page is routed at.

    Stated rather than inferred from the filename, because these share one
    namespace with the docs slugs (``DocsUI`` routes every guide at its slug) and
    ``st.navigation`` rejects a duplicate at start-up. As plain strings they can
    be checked against the docs slugs by a test; a ``StreamlitPage``'s own
    ``url_path`` cannot, since ``st.Page`` skips its initialisation entirely
    outside a script run.
    """

    PERSONAL = "personal"
    JOINT = "joint"
    QUICK_EXPENSES = "quick"
    SETTINGS = "settings"
    LOGIN = "login"


class Pages(enum.Enum):
    """File paths for each page in the application."""

    PERSONAL = st.Page(
        "driving_adapters/pages/personal.py",
        title="Personal",
        icon=":material/dashboard:",
        url_path=PagePaths.PERSONAL,
    )
    JOINT = st.Page(
        "driving_adapters/pages/joint.py",
        title="Joint",
        icon=":material/group:",
        url_path=PagePaths.JOINT,
    )
    QUICK_EXPENSES = st.Page(
        "driving_adapters/pages/quick_expenses.py",
        title="Quick Expenses",
        icon=":material/bolt:",
        url_path=PagePaths.QUICK_EXPENSES,
    )
    SETTINGS = st.Page(
        "driving_adapters/pages/settings.py",
        title="Settings",
        icon=":material/settings:",
        url_path=PagePaths.SETTINGS,
    )
    LOGIN = st.Page(
        "driving_adapters/pages/login.py",
        title="Login",
        icon=":material/lock:",
        url_path=PagePaths.LOGIN,
    )
