"""Unit tests for the Supabase client's request-execution error translation."""

import pytest

from driven_adapters import errors
from driven_adapters.supabase import client


def test_execute_returns_the_request_result_on_success() -> None:
    # Arrange / Act
    result = client._execute(lambda: "ok")

    # Assert
    assert result == "ok"


def test_execute_translates_a_transport_failure_to_supabase_adapter_error() -> None:
    # Arrange
    boom = ConnectionError("network down")

    def _fail() -> object:
        raise boom

    # Act
    with pytest.raises(errors.SupabaseAdapterError) as exc_info:
        client._execute(_fail)

    # Assert - the original transport error is preserved as the chained cause
    assert exc_info.value.__cause__ is boom
