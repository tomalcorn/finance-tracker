"""Error types for the adapter layer.

Adapter code catches low-level exceptions (Supabase HTTP errors, network
failures, validation errors) and re-raises them as AdapterError subclasses.
Use-case code should never see raw Supabase or httpx exceptions.
"""


class AdapterError(Exception):
    """Base class for all adapter-layer errors."""


class SupabaseAdapterError(AdapterError):
    """Raised when a Supabase operation fails (network, HTTP, or query error)."""
