"""Port for authenticating the persistence backend for a user session.

The application needs a way to authenticate its backend as the current user
without knowing how that backend proves identity (JWTs, API keys, sessions).
The driving side depends on this port to keep credentials fresh; a concrete
driven adapter supplies the mechanism.
"""

import abc
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import datetime


class Authenticator(abc.ABC):
    """Authenticates the persistence backend as a given user."""

    @abc.abstractmethod
    def authenticate(self, user_id: str) -> "datetime.datetime | None":
        """Authenticate the backend as ``user_id``.

        Args:
            user_id: The identity to authenticate as.

        Returns:
            When the credentials expire and re-authentication is required, or
            ``None`` if they do not expire.

        Raises:
            AuthenticationError: the backend could not be authenticated.

        """
