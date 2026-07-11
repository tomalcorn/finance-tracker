"""Page-boundary error handling for the Streamlit UI.

Wraps the risky calls a page makes into repositories and use cases so a
``RepositoryError`` or ``UseCaseError`` surfaces as a friendly ``st.error``
instead of a raw Streamlit traceback. Both error types live in inward layers the
UI already depends on, so the boundary needs no import from ``driven_adapters``.
Anything outside those two hierarchies (a genuine programming bug) is left to
propagate untouched.
"""

import contextlib
import logging
from typing import TYPE_CHECKING

import streamlit as st

from ports import errors as port_errors
from use_cases import errors as use_case_errors

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)

_BOUNDARY_ERRORS = (port_errors.RepositoryError, use_case_errors.UseCaseError)


@contextlib.contextmanager
def boundary(section: str) -> "Iterator[None]":
    """Show a friendly error and halt the run if ``section`` fails.

    Catches the domain and use-case errors a page can provoke, logs the full
    traceback for diagnosis, renders a user-facing message, and stops the script
    run. Any other exception propagates unchanged so real bugs still surface.

    Args:
        section: Human-readable name of what was being done, e.g.
            "reconciling your subscriptions".

    """
    try:
        yield
    except _BOUNDARY_ERRORS:
        logger.exception("Boundary error while %s.", section)
        st.error(
            f"Something went wrong while {section}. "
            "Please try again or contact support.",
        )
        st.stop()
