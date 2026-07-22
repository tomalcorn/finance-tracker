"""Unit tests for the contribute button."""

import pytest

from driving_adapters.components.buttons import contribute_button


class TestCanSubmit:
    """Tests for the submit-gating logic on the contribute dialog."""

    @pytest.mark.parametrize(
        ("amount", "from_account_id", "to_account_id", "expected"),
        [
            pytest.param(100.0, "from-1", "to-1", True, id="all_present"),
            pytest.param(None, "from-1", "to-1", False, id="amount_missing"),
            pytest.param(0.0, "from-1", "to-1", False, id="amount_zero"),
            pytest.param(-5.0, "from-1", "to-1", False, id="amount_negative"),
            pytest.param(100.0, None, "to-1", False, id="source_missing"),
            pytest.param(100.0, "from-1", None, False, id="destination_missing"),
        ],
    )
    def test_can_submit(
        self,
        amount: float | None,
        from_account_id: str | None,
        to_account_id: str | None,
        *,
        expected: bool,
    ) -> None:
        # Arrange / Act
        result = contribute_button._can_submit(amount, from_account_id, to_account_id)

        # Assert
        assert result is expected
