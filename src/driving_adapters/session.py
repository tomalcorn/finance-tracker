"""Session-scoped run-once helpers for the Streamlit entry point."""

from typing import TYPE_CHECKING

import streamlit as st

if TYPE_CHECKING:
    from collections.abc import Callable

    from driving_adapters import ss_keys


def run_once_per_session(key: "ss_keys.SSKeys", action: "Callable[[], None]") -> None:
    """Run ``action`` only on the first script run of a session.

    The first call runs ``action`` and marks ``key`` in session state; later
    calls in the same session are no-ops. If ``action`` raises, ``key`` is left
    unset so the next rerun retries.

    Args:
        key: The session-state key that records the action has run.
        action: The side-effecting callable to run at most once per session.

    """
    if key in st.session_state:
        return
    action()
    st.session_state[key] = True
