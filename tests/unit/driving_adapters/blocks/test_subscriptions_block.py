"""Tests for the subscriptions block's grid configuration."""

from collections.abc import Callable
from typing import Any

import pytest

from driving_adapters.blocks import subscriptions_block
from driving_adapters.models import frontend_models


@pytest.fixture(name="subscriptions_config")
def _subscriptions_config(
    build_stub_data_source: Callable[..., Any],
) -> frontend_models.DFEConfig:
    """Return the plain subscriptions grid config, over an empty data source."""
    return subscriptions_block._build_config(
        build_stub_data_source(),
        bank_account_map={"bank-1": "Current"},
        expense_source_map={"expense-1": "Streaming"},
        split_out_contributions=False,
    )


def _column(
    config: frontend_models.DFEConfig,
    column_name: str,
) -> frontend_models.DFEColumnConfig:
    """Return the named column config from a grid config."""
    return next(
        column for column in config.display.columns if column.column_name == column_name
    )


class TestNonNullableCellsCannotBeCleared:
    """A cell edit is a raw column patch that never passes the entity gate.

    So a cleared cell saves ``null`` and crashes the next read against a
    ``SubscriptionView`` field that does not admit one — the same defect found
    on the payments grids (#237).
    """

    @pytest.mark.parametrize(
        "column_name",
        ["name", "amount", "cadence", "bank_account_id", "start_date", "is_active"],
    )
    def test_the_column_is_required(
        self,
        subscriptions_config: frontend_models.DFEConfig,
        column_name: str,
    ) -> None:
        """The editor refuses to submit an emptied non-nullable cell."""
        # Arrange / Act
        column = _column(subscriptions_config, column_name)

        # Assert
        assert column.column_config["required"] is True


class TestNullableCellsStayClearable:
    """The guard tracks the read model, so a nullable column must not get it."""

    def test_the_end_date_cell_is_not_required(
        self,
        subscriptions_config: frontend_models.DFEConfig,
    ) -> None:
        """An ongoing subscription has no end date, so the cell must clear."""
        # Arrange / Act
        column = _column(subscriptions_config, "end_date")

        # Assert
        assert not column.column_config.get("required")

    def test_the_expense_source_cell_is_not_required(
        self,
        subscriptions_config: frontend_models.DFEConfig,
    ) -> None:
        """The expense source is nullable on the view, so the cell must clear."""
        # Arrange / Act
        column = _column(subscriptions_config, "expense_source_id")

        # Assert
        assert not column.column_config.get("required")
