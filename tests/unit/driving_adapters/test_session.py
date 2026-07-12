"""Unit tests for the run-once-per-session helper."""

import pytest
import streamlit as st

from driving_adapters import session, ss_keys

_KEY = ss_keys.SSKeys.WORKSPACE_INITIALISED


def test_runs_the_action_on_the_first_call() -> None:
    # Arrange
    calls: list[int] = []

    # Act
    session.run_once_per_session(_KEY, lambda: calls.append(1))

    # Assert
    assert calls == [1]


def test_does_not_rerun_the_action_once_marked() -> None:
    # Arrange - a prior run already marked the key
    st.session_state[_KEY] = True
    calls: list[int] = []

    # Act
    session.run_once_per_session(_KEY, lambda: calls.append(1))

    # Assert
    assert calls == []


def test_runs_exactly_once_across_repeated_calls() -> None:
    # Arrange
    calls: list[int] = []

    # Act - simulate several script reruns in one session
    for _ in range(3):
        session.run_once_per_session(_KEY, lambda: calls.append(1))

    # Assert
    assert calls == [1]


def test_leaves_the_key_unset_when_the_action_raises() -> None:
    # Arrange
    def _boom() -> None:
        msg = "init failed"
        raise RuntimeError(msg)

    # Act - a failed action must not mark the session, so the next run retries
    with pytest.raises(RuntimeError):
        session.run_once_per_session(_KEY, _boom)

    # Assert
    assert _KEY not in st.session_state
