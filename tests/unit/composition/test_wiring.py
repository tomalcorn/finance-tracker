"""Unit tests for the composition root's Supabase connection.

The connection, signed-in user and JWT secret are swapped for stubs, so no
Streamlit session or secrets are needed.
"""

import types
from collections.abc import Callable
from typing import Any

import jwt
import pytest

from composition import wiring

_SECRET = "unit-test-secret"  # noqa: S105 - test JWT secret, not a real credential
_USER = "auth0|test-user-1"


class _StubConnection:
    """Records the tokens applied to its PostgREST client."""

    def __init__(self) -> None:
        self.applied_tokens: list[str] = []
        self.client = types.SimpleNamespace(
            postgrest=types.SimpleNamespace(auth=self.applied_tokens.append),
        )


def _user_id_in(token: str) -> object:
    claims = jwt.decode(token, _SECRET, algorithms=["HS256"], audience="authenticated")
    return claims["userId"]


@pytest.fixture(name="serve_connection")
def _serve_connection(monkeypatch: pytest.MonkeyPatch) -> Callable[..., Any]:
    """Make wiring hand out ``connection`` as this session's, signed in as _USER."""
    monkeypatch.setattr(wiring, "_jwt_secret", lambda: _SECRET)
    monkeypatch.setattr(wiring.auth, "get_current_user", lambda: _USER)

    def _serve(connection: _StubConnection) -> None:
        monkeypatch.setattr(wiring, "_connection", lambda: connection)

    return _serve


def test_connection_is_cached_per_session() -> None:
    # Arrange
    connection_class = wiring.SessionSupabaseConnection

    # Act
    scope = connection_class.scope()

    # Assert - a "global" connection would share one user's token with every session
    assert scope == "session"


def test_repository_connection_is_authenticated_as_the_current_user(
    serve_connection: Callable[..., Any],
) -> None:
    # Arrange
    connection = _StubConnection()
    serve_connection(connection)

    # Act
    wiring.bank_account_data_source()

    # Assert
    assert _user_id_in(connection.applied_tokens[-1]) == _USER


def test_a_rebuilt_connection_is_authenticated_before_use(
    serve_connection: Callable[..., Any],
) -> None:
    # Arrange - Streamlit rebuilds a session's connection after a reconnect
    serve_connection(_StubConnection())
    wiring.bank_account_data_source()
    rebuilt = _StubConnection()
    serve_connection(rebuilt)

    # Act
    wiring.category_data_source()

    # Assert - without a token it would query as no user, or with the anon key
    assert _user_id_in(rebuilt.applied_tokens[-1]) == _USER
