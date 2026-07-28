"""Main entry point."""

import logging

import streamlit as st

from composition import wiring
from driving_adapters import auth, session, ss_keys
from driving_adapters.pages import constants, docs_pages
from use_cases import errors as use_case_errors

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

st.set_page_config(layout="wide")

if not st.user.is_logged_in:
    st.login("auth0")
    st.stop()

current_user = auth.get_current_user()
auth.ensure_authenticated(wiring.authenticator(), current_user)


def _initialise_workspace() -> None:
    try:
        wiring.workspace_init_use_case().execute()
    except use_case_errors.WorkspaceInitializationError:
        st.error("Could not set up your workspace. Please contact support.")
        logger.exception("Workspace initialization failed")
        st.stop()


def _initialise_joint_workspace() -> None:
    """Seed the current user's joint account once per session, if they have one.

    Seeding is a no-op for a user in no joint account, so this runs for everyone.
    Unlike the personal init it only logs on failure: joint membership is
    optional, so a joint hiccup must not lock the user out of Personal.
    """
    try:
        wiring.joint_workspace_init_use_case().execute()
    except use_case_errors.JointWorkspaceInitializationError:
        st.error("Could not set up your joint workspace. Please contact support.")
        logger.exception("Joint workspace initialization failed")


session.run_once_per_session(
    ss_keys.SSKeys.WORKSPACE_INITIALISED,
    _initialise_workspace,
)

session.run_once_per_session(
    ss_keys.SSKeys.JOINT_WORKSPACE_INITIALISED,
    _initialise_joint_workspace,
)

docs_registry = docs_pages.DocsRegistry(docs_pages.DOCS_DIR)
docs_ui = docs_pages.DocsUI(docs_registry)

pg = st.navigation(
    {
        "": [
            constants.Pages.PERSONAL.value,
            constants.Pages.JOINT.value,
            constants.Pages.QUICK_EXPENSES.value,
            constants.Pages.LOGIN.value,
        ],
        ":material/docs: Docs": docs_ui.build_pages(),
    },
    position="top",
)
pg.run()
