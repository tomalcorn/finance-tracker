"""Unit tests for the payments block grid configs."""

import pydantic

from domain import entities
from driving_adapters.blocks import payments_block
from driving_adapters.models import frontend_models


class _StubDataSource:
    """GridDataSource stub; only exists to satisfy the protocol."""

    def rows(self) -> list[pydantic.BaseModel]:
        return []

    # column_name is unused: the stub only satisfies the GridDataSource protocol.
    def unique_values(self, column_name: str) -> set[object]:  # noqa: ARG002
        return set()

    def apply(self, updates: entities.BackendUpdates) -> None:  # noqa: ARG002
        return None


def _expense_source_column(
    config: frontend_models.DFEConfig,
) -> frontend_models.DFEColumnConfig:
    """Return the expense_source_id column config from an expense grid config."""
    return next(
        c for c in config.display.columns if c.column_name == "expense_source_id"
    )


def test_expense_source_is_optional_in_add_dialog() -> None:
    # Arrange
    config = payments_block._build_expense_config(
        data_source=_StubDataSource(),
        bank_account_ids=["bank-1"],
        get_bank_account_name=str,
        expense_source_ids=["source-1"],
        get_expense_source_name=str,
    )

    # Act
    expense_source_column = _expense_source_column(config)

    # Assert - an expense entry may record money leaving an account with no
    # attributed source (e.g. a transfer between personal accounts).
    assert expense_source_column.required is False
