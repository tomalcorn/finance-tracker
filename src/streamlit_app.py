"""Main entry point."""

import logging

import streamlit as st

from apps.pages import constants, docs_pages
from composition import wiring
from libs import auth, ss_keys
from use_cases import errors as use_case_errors

logger = logging.getLogger(__name__)

st.set_page_config(layout="wide")

if not st.user.is_logged_in:
    st.login("auth0")
    st.stop()

if not st.session_state.get(ss_keys.SSKeys.FIRST_PASS):
    st.session_state[ss_keys.SSKeys.FIRST_PASS] = True

if st.session_state[ss_keys.SSKeys.FIRST_PASS]:
    current_user = auth.get_current_user()
    auth.authenticate_supabase(current_user)
    try:
        wiring.workspace_init_use_case().execute()
    except use_case_errors.WorkspaceInitializationError:
        st.error("Could not set up your workspace. Please contact support.")
        logger.exception("Workspace initialization failed")
        st.stop()
    st.session_state[ss_keys.SSKeys.FIRST_PASS] = False

docs_registry = docs_pages.DocsRegistry(docs_pages.DOCS_DIR)
docs_ui = docs_pages.DocsUI(docs_registry)

pg = st.navigation(
    {
        "": [constants.Pages.DASHBOARD.value, constants.Pages.LOGIN.value],
        ":material/docs: Docs": docs_ui.build_pages(),
    },
    position="top",
)
pg.run()
