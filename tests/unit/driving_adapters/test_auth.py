"""Unit tests for session credential management in the driving auth module.

Drives ``ensure_authenticated`` against a fake ``Authenticator`` port, so these
tests know nothing about JWTs or Supabase — that lives behind the port.
"""

import datetime

import streamlit as st

from driving_adapters import auth, ss_keys
from ports import authentication

_USER = "auth0|test-user-1"


class _FakeAuthenticator(authentication.Authenticator):
    """Records authenticate calls and returns a fixed expiry."""

    def __init__(self, expiry: datetime.datetime | None) -> None:
        self._expiry = expiry
        self.calls: list[str] = []

    def authenticate(self, user_id: str) -> datetime.datetime | None:
        self.calls.append(user_id)
        return self._expiry


def _in(minutes: int) -> datetime.datetime:
    """Return an aware timestamp ``minutes`` from now."""
    return datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(minutes=minutes)


def test_authenticates_when_the_session_has_no_credentials() -> None:
    # Arrange
    authenticator = _FakeAuthenticator(_in(60))

    # Act
    auth.ensure_authenticated(authenticator, _USER)

    # Assert
    assert authenticator.calls == [_USER]


def test_records_the_returned_expiry_in_session_state() -> None:
    # Arrange
    expiry = _in(60)
    authenticator = _FakeAuthenticator(expiry)

    # Act
    auth.ensure_authenticated(authenticator, _USER)

    # Assert
    assert st.session_state[ss_keys.SSKeys.AUTH_CREDENTIALS_EXP] == expiry


def test_does_not_reauthenticate_credentials_that_are_still_fresh() -> None:
    # Arrange - expiry well outside the refresh margin
    st.session_state[ss_keys.SSKeys.AUTH_CREDENTIALS_EXP] = _in(60)
    authenticator = _FakeAuthenticator(_in(60))

    # Act
    auth.ensure_authenticated(authenticator, _USER)

    # Assert
    assert authenticator.calls == []


def test_reauthenticates_credentials_within_the_refresh_margin() -> None:
    # Arrange - expiry inside the 5-minute margin
    st.session_state[ss_keys.SSKeys.AUTH_CREDENTIALS_EXP] = _in(1)
    authenticator = _FakeAuthenticator(_in(60))

    # Act
    auth.ensure_authenticated(authenticator, _USER)

    # Assert
    assert authenticator.calls == [_USER]


def test_does_not_reauthenticate_a_non_expiring_credential() -> None:
    # Arrange - a backend whose credentials never expire authenticated once
    st.session_state[ss_keys.SSKeys.AUTH_CREDENTIALS_EXP] = None
    authenticator = _FakeAuthenticator(None)

    # Act
    auth.ensure_authenticated(authenticator, _USER)

    # Assert
    assert authenticator.calls == []
