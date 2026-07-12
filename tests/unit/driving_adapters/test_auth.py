"""Unit tests for Supabase JWT minting and refresh.

The Supabase connection is stubbed to record applied tokens, and the JWT
secret is substituted for a test value so no live secrets are needed.
"""

import time
import types
from typing import TYPE_CHECKING, cast

import jwt
import pytest
import streamlit as st

from driving_adapters import auth, ss_keys

if TYPE_CHECKING:
    import st_supabase_connection

_SECRET = "unit-test-secret"  # noqa: S105 - test JWT secret, not a real credential
_USER = "auth0|test-user-1"


@pytest.fixture(autouse=True)
def _patch_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """Supply a test JWT secret in place of the live Streamlit secret."""
    monkeypatch.setattr(
        st,
        "secrets",
        {"supabase_admin": {"jwt_secret": _SECRET}},
    )


class _StubConnection:
    """Records the tokens applied to the PostgREST client."""

    def __init__(self) -> None:
        self.applied_tokens: list[str] = []
        self.client = types.SimpleNamespace(
            postgrest=types.SimpleNamespace(auth=self.applied_tokens.append),
        )


def _as_connection(
    stub: _StubConnection,
) -> "st_supabase_connection.SupabaseConnection":
    """Cast the stub to the connection type (it duck-types the auth call)."""
    return cast("st_supabase_connection.SupabaseConnection", stub)


class TestMintSupabaseJwt:
    def test_returned_expiry_matches_the_token_exp_claim(self) -> None:
        # Act
        token, exp = auth._mint_supabase_jwt(_USER)

        # Assert - the returned exp is what callers track refresh against
        decoded = jwt.decode(
            token,
            _SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        assert decoded["exp"] == exp

    def test_token_carries_the_auth0_user_id(self) -> None:
        # Act
        token, _ = auth._mint_supabase_jwt(_USER)

        # Assert - the userId claim drives Supabase RLS
        decoded = jwt.decode(
            token,
            _SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        assert decoded["userId"] == _USER


class TestEnsureSupabaseAuthenticated:
    def test_mints_a_token_when_the_session_has_none(self) -> None:
        # Arrange
        connection = _StubConnection()

        # Act
        auth.ensure_supabase_authenticated(_USER, _as_connection(connection))

        # Assert
        assert len(connection.applied_tokens) == 1

    def test_records_the_expiry_in_session_state(self) -> None:
        # Arrange
        connection = _StubConnection()

        # Act
        auth.ensure_supabase_authenticated(_USER, _as_connection(connection))

        # Assert
        assert ss_keys.SSKeys.SUPABASE_TOKEN_EXP in st.session_state

    def test_does_not_remint_a_still_fresh_token(self) -> None:
        # Arrange - a token issued this session that is nowhere near expiry
        connection = _StubConnection()
        st.session_state[ss_keys.SSKeys.SUPABASE_TOKEN_EXP] = int(time.time()) + 3600

        # Act
        auth.ensure_supabase_authenticated(_USER, _as_connection(connection))

        # Assert
        assert connection.applied_tokens == []

    def test_remints_a_token_within_the_refresh_margin(self) -> None:
        # Arrange - expiry is inside the refresh window, so it must re-mint
        connection = _StubConnection()
        st.session_state[ss_keys.SSKeys.SUPABASE_TOKEN_EXP] = int(time.time()) + 60

        # Act
        auth.ensure_supabase_authenticated(_USER, _as_connection(connection))

        # Assert
        assert len(connection.applied_tokens) == 1
