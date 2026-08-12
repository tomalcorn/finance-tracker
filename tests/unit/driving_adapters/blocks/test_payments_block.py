"""Tests for the payments block's grid configuration."""

from collections.abc import Callable
from typing import Any

import pytest

from driving_adapters.blocks import payments_block
from driving_adapters.models import frontend_models


@pytest.fixture(name="income_config")
def _income_config(
    build_stub_data_source: Callable[..., Any],
) -> frontend_models.DFEConfig:
    """Return the income grid config, built over an empty data source."""
    _, income_config, _, _ = payments_block._configs(
        build_stub_data_source(),
        bank_account_map={"bank-1": "Current"},
        expense_source_map={"expense-1": "Groceries"},
        income_source_map={"income-1": "Salary"},
    )
    return income_config


@pytest.fixture(name="expense_config")
def _expense_config(
    build_stub_data_source: Callable[..., Any],
) -> frontend_models.DFEConfig:
    """Return the expense grid config, built over an empty data source."""
    expense_config, _, _, _ = payments_block._configs(
        build_stub_data_source(),
        bank_account_map={"bank-1": "Current"},
        expense_source_map={"expense-1": "Groceries"},
        income_source_map={"income-1": "Salary"},
    )
    return expense_config


def _column(
    config: frontend_models.DFEConfig,
    column_name: str,
) -> frontend_models.DFEColumnConfig:
    """Return the named column config from a grid config."""
    return next(
        column for column in config.display.columns if column.column_name == column_name
    )


class TestPaymentSourcesAreOptional:
    """Neither leg of a transfer between your own accounts has a source (#231)."""

    def test_income_source_is_not_required(
        self,
        income_config: frontend_models.DFEConfig,
    ) -> None:
        """An income payment can be added without an income source."""
        # Arrange / Act
        column = _column(income_config, "income_source_id")

        # Assert
        assert column.required is False

    def test_expense_source_is_not_required(
        self,
        expense_config: frontend_models.DFEConfig,
    ) -> None:
        """The expense side stays optional, so the two legs match."""
        # Arrange / Act
        column = _column(expense_config, "expense_source_id")

        # Assert
        assert column.required is False

    @pytest.mark.parametrize("column_name", ["name", "payment_date", "income"])
    def test_other_income_columns_stay_required(
        self,
        income_config: frontend_models.DFEConfig,
        column_name: str,
    ) -> None:
        """Only the source became optional; the rest of the row is still needed."""
        # Arrange / Act
        column = _column(income_config, column_name)

        # Assert
        assert column.required is True


class TestNonNullableCellsCannotBeCleared:
    """``DFEColumnConfig.required`` guards the add dialog; this guards the cell.

    Clearing a cell of a stored row is an edit, and an edit is a raw column
    patch that never passes the entity gate — so a blank one reached the
    database as ``null`` and crashed the next read, which validates it against
    a ``PaymentView`` field that does not admit one (#237).
    """

    @pytest.mark.parametrize(
        "column_name",
        ["name", "payment_date", "expense", "checked", "bank_account_id"],
    )
    def test_expense_columns_are_required(
        self,
        expense_config: frontend_models.DFEConfig,
        column_name: str,
    ) -> None:
        """The editor refuses to submit an emptied non-nullable expense cell."""
        # Arrange / Act
        column = _column(expense_config, column_name)

        # Assert
        assert column.column_config["required"] is True

    @pytest.mark.parametrize(
        "column_name",
        ["name", "payment_date", "income", "checked", "bank_account_id"],
    )
    def test_income_columns_are_required(
        self,
        income_config: frontend_models.DFEConfig,
        column_name: str,
    ) -> None:
        """The editor refuses to submit an emptied non-nullable income cell."""
        # Arrange / Act
        column = _column(income_config, column_name)

        # Assert
        assert column.column_config["required"] is True


class TestNullableCellsStayClearable:
    """The guard tracks the read model, so a nullable column must not get it.

    The source columns are the ones a transfer between your own accounts leaves
    empty (#231); making them required would break that.
    """

    def test_the_expense_source_cell_is_not_required(
        self,
        expense_config: frontend_models.DFEConfig,
    ) -> None:
        """An expense source can still be cleared."""
        # Arrange / Act
        column = _column(expense_config, "expense_source_id")

        # Assert
        assert not column.column_config.get("required")

    def test_the_income_source_cell_is_not_required(
        self,
        income_config: frontend_models.DFEConfig,
    ) -> None:
        """An income source can still be cleared."""
        # Arrange / Act
        column = _column(income_config, "income_source_id")

        # Assert
        assert not column.column_config.get("required")
