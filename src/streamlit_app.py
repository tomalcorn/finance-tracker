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


session.run_once_per_session(
    ss_keys.SSKeys.WORKSPACE_INITIALISED,
    _initialise_workspace,
)

docs_registry = docs_pages.DocsRegistry(docs_pages.DOCS_DIR)
docs_ui = docs_pages.DocsUI(docs_registry)

# The Joint page (constants.Pages.JOINT) is deliberately not registered yet:
# the joint workflow lands as one breaking change in the final Joint ticket.
# The page and its wiring stay in the tree, ready to be added here then.
pg = st.navigation(
    {
        "": [
            constants.Pages.PERSONAL.value,
            constants.Pages.LOGIN.value,
        ],
        ":material/docs: Docs": docs_ui.build_pages(),
    },
    position="top",
)
pg.run()
