"""Errors raised across the persistence ports.

A port defines what the application needs from persistence, and its failure
contract is part of that port. Concrete adapters translate their own low-level
failures into these port-level errors at the boundary, so callers on either
side depend only on this abstract contract, never on an adapter's internals.
"""


class PortError(Exception):
    """Base class for errors raised across a persistence port."""


class RepositoryError(PortError):
    """Raised when a repository operation fails to read or write an aggregate.

    The concrete implementation translates its own low-level failures into this
    type at the port boundary, so callers can catch it without depending on the
    adapter that raised it.
    """


class NoJointAccountError(RepositoryError):
    """Raised when a joint-scoped repository is used without a joint account.

    A joint repository reads and writes the rows of the user's joint account, so
    it has nothing to act on when the user belongs to none. A caller that can
    offer to create one (the joint dashboard) catches this specifically; anything
    else lets it surface as the ``RepositoryError`` it is.
    """

    def __init__(self, user_id: str) -> None:
        """Construct NoJointAccountError.

        Args:
            user_id: The user who belongs to no joint account.

        """
        self.user_id = user_id
        super().__init__(f"User {user_id!r} belongs to no joint account.")


class AuthenticationError(PortError):
    """Raised when the backend cannot be authenticated for a user.

    The concrete authenticator translates its own low-level failures (JWT
    minting, backend auth calls) into this type at the port boundary.
    """
