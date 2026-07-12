"""Unit tests for the Supabase authenticator.

The PostgREST client is stubbed to record applied tokens; the JWT secret is a
plain test value, so no Streamlit secrets are needed.
"""

import datetime
import types
from typing import TYPE_CHECKING, cast

import jwt
import pytest

from driven_adapters.supabase import authenticator as supabase_auth
from ports import errors

if TYPE_CHECKING:
    import st_supabase_connection

_SECRET = "unit-test-secret"  # noqa: S105 - test JWT secret, not a real credential
_USER = "auth0|test-user-1"


class _StubConnection:
    """Records the tokens applied to the PostgREST client, or raises on auth."""

    def __init__(self, auth_error: Exception | None = None) -> None:
        self.applied_tokens: list[str] = []

        def _auth(token: str) -> None:
            if auth_error is not None:
                raise auth_error
            self.applied_tokens.append(token)

        self.client = types.SimpleNamespace(
            postgrest=types.SimpleNamespace(auth=_auth),
        )


def _as_connection(
    stub: _StubConnection,
) -> "st_supabase_connection.SupabaseConnection":
    """Cast the stub to the connection type (it duck-types the auth call)."""
    return cast("st_supabase_connection.SupabaseConnection", stub)


def _decode(token: str) -> dict[str, object]:
    return jwt.decode(token, _SECRET, algorithms=["HS256"], audience="authenticated")


def test_applies_a_token_carrying_the_user_id_claim() -> None:
    # Arrange
    connection = _StubConnection()
    authenticator = supabase_auth.SupabaseAuthenticator(
        _as_connection(connection),
        _SECRET,
    )

    # Act
    authenticator.authenticate(_USER)

    # Assert - the userId claim drives Supabase RLS
    assert _decode(connection.applied_tokens[0])["userId"] == _USER


def test_returned_expiry_matches_the_token_exp_claim() -> None:
    # Arrange
    connection = _StubConnection()
    authenticator = supabase_auth.SupabaseAuthenticator(
        _as_connection(connection),
        _SECRET,
    )

    # Act
    expires_at = authenticator.authenticate(_USER)

    # Assert
    assert int(expires_at.timestamp()) == _decode(connection.applied_tokens[0])["exp"]


def test_expiry_is_about_an_hour_ahead() -> None:
    # Arrange
    connection = _StubConnection()
    authenticator = supabase_auth.SupabaseAuthenticator(
        _as_connection(connection),
        _SECRET,
    )
    before = datetime.datetime.now(tz=datetime.UTC)

    # Act
    expires_at = authenticator.authenticate(_USER)

    # Assert - within a minute of one hour from now
    drift = abs((expires_at - before) - datetime.timedelta(hours=1))
    assert drift < datetime.timedelta(minutes=1)


def test_translates_a_backend_auth_failure() -> None:
    # Arrange
    boom = ConnectionError("postgrest down")
    connection = _StubConnection(auth_error=boom)
    authenticator = supabase_auth.SupabaseAuthenticator(
        _as_connection(connection),
        _SECRET,
    )

    # Act
    with pytest.raises(errors.AuthenticationError) as exc_info:
        authenticator.authenticate(_USER)

    # Assert - the original failure is preserved as the chained cause
    assert exc_info.value.__cause__ is boom
