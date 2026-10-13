"""Unit tests for the composition root's Supabase connection."""

from composition import wiring


def test_connection_is_cached_per_session() -> None:
    # Arrange
    connection_class = wiring.SessionSupabaseConnection

    # Act
    scope = connection_class.scope()

    # Assert - a "global" connection would share one user's token with every session
    assert scope == "session"
