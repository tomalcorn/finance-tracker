"""Unit tests for the UI page-boundary error handler.

A stub stands in for the ``streamlit`` module so the tests assert behaviour
(message shown, run halted) rather than real Streamlit calls. ``st.stop`` in
real Streamlit raises to abort the run, so the stub models that with
``_HaltError``.
"""

import pytest

from domain import errors as domain_errors
from driving_adapters import error_boundary
from use_cases import errors as use_case_errors


class _HaltError(Exception):
    """Sentinel mirroring the abort ``st.stop`` raises to end the script run."""


class _StubStreamlit:
    """Records ``st.error`` messages; ``st.stop`` aborts like the real thing."""

    def __init__(self) -> None:
        self.errors: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def stop(self) -> None:
        raise _HaltError


_BOUNDARY_ERRORS = [
    domain_errors.RepositoryError("read failed"),
    use_case_errors.UseCaseError("use case failed"),
    use_case_errors.ReconciliationError("reconcile failed"),
    use_case_errors.DataAccessError("data access failed"),
    use_case_errors.AmountToBankLTEZeroError("Groceries"),
]


@pytest.mark.parametrize("error", _BOUNDARY_ERRORS)
def test_boundary_halts_on_domain_and_use_case_errors(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    # Arrange
    monkeypatch.setattr(error_boundary, "st", _StubStreamlit())

    # Act / Assert - reaching st.stop (the _HaltError) proves the run was aborted
    with pytest.raises(_HaltError), error_boundary.boundary("loading your dashboard"):
        raise error


def test_boundary_shows_the_section_in_the_error_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    stub = _StubStreamlit()
    monkeypatch.setattr(error_boundary, "st", stub)

    # Act
    failure = domain_errors.RepositoryError("boom")
    with pytest.raises(_HaltError), error_boundary.boundary("reconciling subs"):
        raise failure

    # Assert
    assert "reconciling subs" in stub.errors[0]


def test_unexpected_error_propagates_untouched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setattr(error_boundary, "st", _StubStreamlit())
    bug = ValueError("genuine bug")

    # Act / Assert - a non-boundary error is a bug and must not be swallowed
    with pytest.raises(ValueError, match="genuine bug"), error_boundary.boundary("x"):
        raise bug
