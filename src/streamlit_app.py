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

    Mirrors ``_initialise_workspace`` but with two differences forced by joint
    membership being optional: a user in no joint account is a silent no-op
    (``NoJointAccountToInitialiseError``), and a genuine seeding failure logs
    without ``st.stop`` — a joint hiccup must not lock the user out of Personal.
    """
    try:
        wiring.joint_workspace_init_use_case().execute()
    except use_case_errors.NoJointAccountToInitialiseError:
        logger.debug("No joint account to initialise for the current user.")
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

# The Joint page self-gates: a user who belongs to no joint account sees a
# prompt explaining how they work rather than any shared data, so it is safe to
# register for everyone (see joint.py).
pg = st.navigation(
    {
        "": [
            constants.Pages.PERSONAL.value,
            constants.Pages.JOINT.value,
            constants.Pages.LOGIN.value,
        ],
        ":material/docs: Docs": docs_ui.build_pages(),
    },
    position="top",
)
pg.run()
