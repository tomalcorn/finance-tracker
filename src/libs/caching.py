"""Custom caching module with partial cache invalidation support."""

import functools
import inspect
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


def _make_hashable(value: Any) -> Any:  # noqa: ANN401
    """Convert a value to a hashable representation recursively.

    Handles dicts, lists, sets, tuples, and Pydantic models (via
    ``model_dump``).  Any other value is returned unchanged; if it is not
    already hashable a ``TypeError`` will be raised when it is used as a
    cache key.

    Args:
        value: The value to convert to a hashable form.

    Returns:
        A hashable equivalent of *value*.

    """
    if isinstance(value, dict):
        return tuple(
            sorted((_make_hashable(k), _make_hashable(v)) for k, v in value.items()),
        )
    if isinstance(value, list):
        return tuple(_make_hashable(v) for v in value)
    if isinstance(value, set):
        return frozenset(_make_hashable(v) for v in value)
    if isinstance(value, tuple):
        return tuple(_make_hashable(v) for v in value)
    if hasattr(value, "model_dump"):
        return _make_hashable(value.model_dump())
    return value


class _CachedFunction[**P, R]:
    """Cached wrapper around a callable.

    Produced by the :func:`cache` decorator.  Behaves identically to the
    wrapped function but stores previous return values and exposes a
    :meth:`clear` method for selective cache invalidation.
    """

    def __init__(self, func: Callable[P, R]) -> None:
        """Wrap *func* with caching behaviour."""
        functools.update_wrapper(self, func)
        self._func = func
        self._cache: dict[tuple[tuple[str, Any], ...], R] = {}
        self._args_store: dict[tuple[tuple[str, Any], ...], dict[str, Any]] = {}
        self._sig = inspect.signature(func)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
        """Return a cached result for *args*/*kwargs*, computing it if necessary."""
        bound = self._sig.bind(*args, **kwargs)
        bound.apply_defaults()
        key_args = {k: v for k, v in bound.arguments.items() if not k.startswith("_")}
        cache_key = tuple((k, _make_hashable(v)) for k, v in sorted(key_args.items()))
        if cache_key not in self._cache:
            self._cache[cache_key] = self._func(*args, **kwargs)
            self._args_store[cache_key] = key_args
        else:
            logger.debug(
                "Cache hit for '%s' with args %s",
                self._func.__name__,
                dict(key_args),
            )
        return self._cache[cache_key]

    def clear(self, **kwargs: Any) -> None:  # noqa: ANN401
        """Clear cached entries, with optional partial matching.

        When called with no arguments, the entire cache is flushed.
        When called with keyword arguments, only entries whose stored argument
        values match *all* provided kwargs are removed — allowing partial
        invalidation across the remaining arguments.

        Example::

            get_data.clear()                        # flush everything
            get_data.clear(table_name="payments")   # all "payments" entries

        Args:
            **kwargs: Argument name/value pairs to match against cached keys.

        Raises:
            ValueError: If a kwarg name is not a cacheable parameter of the
                wrapped function (i.e. not a non-underscore-prefixed parameter).

        """
        if not kwargs:
            logger.debug("Cache cleared for '%s'", self._func.__name__)
            self._cache.clear()
            self._args_store.clear()
            return

        valid_params = {k for k in self._sig.parameters if not k.startswith("_")}
        for k in kwargs:
            if k not in valid_params:
                msg = (
                    f"'{k}' is not a cacheable parameter of"
                    f" '{self._func.__name__}'. "
                    f"Cacheable parameters are: {sorted(valid_params)}"
                )
                raise ValueError(msg)

        keys_to_remove = [
            key
            for key, args_dict in self._args_store.items()
            if all(args_dict.get(k) == v for k, v in kwargs.items())
        ]
        logger.debug(
            "Cache cleared for '%s' matching %s (%d entr%s removed)",
            self._func.__name__,
            kwargs,
            len(keys_to_remove),
            "y" if len(keys_to_remove) == 1 else "ies",
        )
        for key in keys_to_remove:
            del self._cache[key]
            del self._args_store[key]


def cache[**P, R](func: Callable[P, R]) -> _CachedFunction[P, R]:
    """Decorate a function to cache its return value with selective invalidation.

    Results are keyed on all non-underscore-prefixed parameters.  Parameters
    whose names start with ``_`` are forwarded to the function but excluded
    from the cache key — useful for unhashable arguments such as database
    connections.

    Unhashable argument values (lists, dicts, sets, Pydantic models, …) are
    converted to a stable hashable form automatically.

    Example::

        @cache
        def get_data(
            table_name: str,
            query_string: str,
            _connection: Connection = default_conn,
        ) -> list[dict]:
            ...

        get_data.clear()                        # flush everything
        get_data.clear(table_name="payments")   # all "payments" entries

    Args:
        func: The callable to wrap.

    Returns:
        A :class:`_CachedFunction` wrapping *func*.

    """
    return _CachedFunction(func)
