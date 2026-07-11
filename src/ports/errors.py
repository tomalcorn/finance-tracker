"""Errors raised across the persistence ports.

A port defines what the application needs from persistence, and its failure
contract is part of that port. Concrete adapters translate their own low-level
failures (Supabase, cache, HTTP) into these port-level errors at the boundary,
so callers on either side — use cases and the driving UI — depend only on this
abstract contract, never on a driven adapter's internals.
"""


class PortError(Exception):
    """Base class for errors raised across a persistence port."""


class RepositoryError(PortError):
    """Raised when a repository operation fails to read or write an aggregate.

    The concrete ``Repository`` implementation translates its low-level failures
    (Supabase, cache, HTTP, including its internal ``AdapterError``) into this
    type at the port boundary, so both use cases and the UI can catch it without
    importing the driven adapter.
    """
