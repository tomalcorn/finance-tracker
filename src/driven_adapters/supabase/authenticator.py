"""Supabase implementation of the authentication port.

Mints a short-lived JWT carrying the user's identity and applies it to the
PostgREST client so Supabase row-level security scopes every request. The JWT
secret is injected by composition, so this adapter never touches Streamlit.
"""

import datetime
from typing import TYPE_CHECKING

import jwt

from ports import authentication, errors

if TYPE_CHECKING:
    import st_supabase_connection

_TOKEN_TTL = datetime.timedelta(hours=1)


class SupabaseAuthenticator(authentication.Authenticator):
    """Authenticate a Supabase connection by minting and applying a user JWT."""

    def __init__(
        self,
        connection: "st_supabase_connection.SupabaseConnection",
        jwt_secret: str,
    ) -> None:
        """Bind the authenticator to a connection and the signing secret."""
        self._connection = connection
        self._jwt_secret = jwt_secret

    def authenticate(self, user_id: str) -> datetime.datetime:
        """Mint a JWT for the user and apply it to the PostgREST client.

        Args:
            user_id: The Auth0 user ID, carried as the ``userId`` claim that the
                custom ``auth.user_id()`` Postgres function reads in RLS policies.

        Returns:
            When the minted token expires.

        Raises:
            AuthenticationError: the token could not be minted or applied.

        """
        issued_at = datetime.datetime.now(tz=datetime.UTC)
        expires_at = issued_at + _TOKEN_TTL
        token = self._mint(user_id, issued_at, expires_at)
        try:
            self._connection.client.postgrest.auth(token)
        except Exception as e:
            msg = f"Failed to authenticate Supabase connection: {e}"
            raise errors.AuthenticationError(msg) from e
        return expires_at

    def _mint(
        self,
        user_id: str,
        issued_at: datetime.datetime,
        expires_at: datetime.datetime,
    ) -> str:
        """Encode the RLS JWT, translating a signing failure at the boundary."""
        payload = {
            "userId": user_id,
            "role": "authenticated",
            "aud": "authenticated",
            "iat": int(issued_at.timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        try:
            return jwt.encode(payload, self._jwt_secret, algorithm="HS256")
        except Exception as e:
            msg = f"Failed to mint Supabase JWT: {e}"
            raise errors.AuthenticationError(msg) from e
