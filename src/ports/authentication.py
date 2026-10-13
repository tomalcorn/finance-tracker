"""Port for authenticating the persistence backend for a user session.

The application needs a way to authenticate its backend as the current user
without knowing how that backend proves identity (JWTs, API keys, sessions).
Composition authenticates through this port before handing a connection to a
repository; a concrete driven adapter supplies the mechanism.
"""

import abc


class Authenticator(abc.ABC):
    """Authenticates the persistence backend as a given user."""

    @abc.abstractmethod
    def authenticate(self, user_id: str) -> None:
        """Authenticate the backend as ``user_id``.

        Args:
            user_id: The identity to authenticate as.

        Raises:
            AuthenticationError: the backend could not be authenticated.

        """
