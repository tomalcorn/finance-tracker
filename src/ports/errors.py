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


class AuthenticationError(PortError):
    """Raised when the backend cannot be authenticated for a user.

    The concrete authenticator translates its own low-level failures (JWT
    minting, backend auth calls) into this type at the port boundary.
    """
