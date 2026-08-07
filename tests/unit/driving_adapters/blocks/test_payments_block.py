"""Tests for the payments block's grid configuration."""

from typing import TYPE_CHECKING

import pytest

from driving_adapters.blocks import payments_block
from driving_adapters.models import frontend_models

if TYPE_CHECKING:
    from tests import conftest


@pytest.fixture(name="income_config")
def _income_config(
    build_stub_data_source: "conftest.StubDataSourceBuilder",
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
    build_stub_data_source: "conftest.StubDataSourceBuilder",
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
