"""Unit tests for the BankButton class."""

import uuid
from unittest import mock

import pytest

from apps.buttons import bank_button
from libs.dfes import constants as dfe_constants

_EXPECTED_CALLS_PER_ITEM = 2

_TABLES_TO_CLEAR = [
    dfe_constants.TableNames.ONE_OFFS,
    dfe_constants.TableNames.ONE_OFFS_VIEW,
    dfe_constants.TableNames.PAYMENTS,
    dfe_constants.TableNames.BANK_ACCOUNTS_VIEW,
    dfe_constants.TableNames.BUDGET_TRACKER,
    dfe_constants.TableNames.BUDGET_TRACKER_VIEW,
]
_ONE_OFFS_TABLE = dfe_constants.TableNames.ONE_OFFS.value


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture(name="bank_btn")
def _bank_btn() -> bank_button.BankButton:
    return bank_button.BankButton(
        one_offs_table=_ONE_OFFS_TABLE,
        tables_to_clear=_TABLES_TO_CLEAR,
    )


@pytest.fixture(name="bank_account_id")
def _bank_account_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture(name="expense_source_id")
def _expense_source_id() -> str:
    return str(uuid.uuid4())


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_item(
    *,
    name: str = "Holiday",
    current_month: float = 100.0,
    banked: float = 50.0,
) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "name": name,
        "current_month": current_month,
        "banked": banked,
    }


# ------------------------------------------------------------------
# TestBankItems
# ------------------------------------------------------------------


class TestBankItems:
    """Tests for BankButton._bank_items."""

    @mock.patch.object(bank_button.data_client, "update_backend")
    def test_single_item_creates_two_backend_calls(
        self,
        mock_update: mock.MagicMock,
        bank_btn: bank_button.BankButton,
        bank_account_id: str,
    ) -> None:
        """Banking one item should produce two update_backend calls."""
        # Arrange
        item = _make_item()

        # Act
        bank_btn._bank_items([item], bank_account_id, expense_source_id=None)

        # Assert
        assert mock_update.call_count == _EXPECTED_CALLS_PER_ITEM

    @pytest.mark.parametrize(
        ("current_month", "banked", "expected_banked"),
        [
            (100.0, 50.0, 150.0),
            (25.0, 0.0, 25.0),
            (0.5, 99.5, 100.0),
        ],
        ids=["standard", "from-zero", "fractional"],
    )
    @mock.patch.object(bank_button.data_client, "update_backend")
    def test_one_off_row_updated_correctly(  # noqa: PLR0913 - needed for test
        self,
        mock_update: mock.MagicMock,
        bank_btn: bank_button.BankButton,
        bank_account_id: str,
        current_month: float,
        banked: float,
        expected_banked: float,
    ) -> None:
        """The one-off row should have banked incremented and current_month zeroed."""
        # Arrange
        item = _make_item(current_month=current_month, banked=banked)

        # Act
        bank_btn._bank_items([item], bank_account_id, expense_source_id=None)

        # Assert
        one_off_call = mock_update.call_args_list[0]
        edited = one_off_call.kwargs["updates"].edited_rows[item["id"]]
        assert all(
            [
                one_off_call.kwargs["table_name"] == _ONE_OFFS_TABLE,
                edited["banked"] == expected_banked,
                edited["current_month"] == 0,
            ],
        )

    @mock.patch.object(bank_button.data_client, "update_backend")
    def test_payment_inserted_with_correct_fields(
        self,
        mock_update: mock.MagicMock,
        bank_btn: bank_button.BankButton,
        bank_account_id: str,
        expense_source_id: str,
    ) -> None:
        """A payment row should be inserted with correct name, amount, and type."""
        # Arrange
        item = _make_item(name="Holiday", current_month=75.0)

        # Act
        bank_btn._bank_items([item], bank_account_id, expense_source_id)

        # Assert
        payment_call = mock_update.call_args_list[1]
        added_row = payment_call.kwargs["updates"].added_rows[0]
        assert all(
            [
                payment_call.kwargs["table_name"]
                == dfe_constants.TableNames.PAYMENTS.value,
                added_row["name"] == "Bank: Holiday",
                added_row["expense"] == item["current_month"],
                added_row["payment_type"] == "expense",
                added_row["bank_account_id"] == bank_account_id,
                added_row["expense_source_id"] == expense_source_id,
            ],
        )

    @mock.patch.object(bank_button.data_client, "update_backend")
    def test_payment_without_expense_source(
        self,
        mock_update: mock.MagicMock,
        bank_btn: bank_button.BankButton,
        bank_account_id: str,
    ) -> None:
        """When expense_source_id is None, the payment should omit it."""
        # Arrange
        item = _make_item(current_month=50.0)

        # Act
        bank_btn._bank_items([item], bank_account_id, expense_source_id=None)

        # Assert
        added_row = mock_update.call_args_list[1].kwargs["updates"].added_rows[0]
        assert "expense_source_id" not in added_row

    @pytest.mark.parametrize(
        "current_month",
        [0.0, -5.0, -100.0],
        ids=["zero", "negative", "large-negative"],
    )
    @mock.patch.object(bank_button.data_client, "update_backend")
    def test_skips_items_with_non_positive_current_month(
        self,
        mock_update: mock.MagicMock,
        bank_btn: bank_button.BankButton,
        bank_account_id: str,
        current_month: float,
    ) -> None:
        """Items with current_month <= 0 should be skipped entirely."""
        # Arrange
        item = _make_item(current_month=current_month)

        # Act
        bank_btn._bank_items([item], bank_account_id, expense_source_id=None)

        # Assert
        mock_update.assert_not_called()

    @pytest.mark.parametrize(
        ("item_count", "expected_calls"),
        [(1, 2), (2, 4), (3, 6)],
        ids=["1-item", "2-items", "3-items"],
    )
    @mock.patch.object(bank_button.data_client, "update_backend")
    def test_call_count_scales_with_items(
        self,
        mock_update: mock.MagicMock,
        bank_btn: bank_button.BankButton,
        bank_account_id: str,
        item_count: int,
        expected_calls: int,
    ) -> None:
        """Banking N items should produce 2*N update_backend calls."""
        # Arrange
        items = [_make_item(current_month=50.0) for _ in range(item_count)]

        # Act
        bank_btn._bank_items(items, bank_account_id, expense_source_id=None)

        # Assert
        assert mock_update.call_count == expected_calls

    @mock.patch.object(bank_button.data_client, "update_backend")
    def test_tables_to_clear_passed_through(
        self,
        mock_update: mock.MagicMock,
        bank_btn: bank_button.BankButton,
        bank_account_id: str,
    ) -> None:
        """Both calls should pass the configured tables_to_clear."""
        # Arrange
        item = _make_item()

        # Act
        bank_btn._bank_items([item], bank_account_id, expense_source_id=None)

        # Assert
        assert all(
            call.kwargs["tables_to_clear"] == _TABLES_TO_CLEAR
            for call in mock_update.call_args_list
        )

    @mock.patch.object(bank_button.data_client, "update_backend")
    def test_banked_defaults_to_zero_when_missing(
        self,
        mock_update: mock.MagicMock,
        bank_btn: bank_button.BankButton,
        bank_account_id: str,
    ) -> None:
        """If item has no 'banked' key, it should default to 0."""
        # Arrange
        item = {"id": str(uuid.uuid4()), "name": "Test", "current_month": 40.0}

        # Act
        bank_btn._bank_items([item], bank_account_id, expense_source_id=None)

        # Assert
        edited = mock_update.call_args_list[0].kwargs["updates"].edited_rows[item["id"]]
        assert edited["banked"] == item["current_month"]


# ------------------------------------------------------------------
# TestGetExpenseSourceId
# ------------------------------------------------------------------


_BT_ONE_OFFS_ID = str(uuid.uuid4())
_EXPENSE_SOURCE_ID = str(uuid.uuid4())


class TestGetExpenseSourceId:
    """Tests for BankButton._get_expense_source_id."""

    @pytest.fixture(name="matching_bt_and_es")
    def _matching_bt_and_es(self) -> list[list[dict]]:
        """Budget tracker + expense source that match."""
        return [
            [{"id": _BT_ONE_OFFS_ID, "name": "One-offs"}],
            [
                {
                    "id": _EXPENSE_SOURCE_ID,
                    "name": "One-offs",
                    "budget_tracker_ids": [_BT_ONE_OFFS_ID],
                },
            ],
        ]

    @mock.patch.object(bank_button.data_client, "get_data")
    def test_returns_matching_expense_source(
        self,
        mock_get_data: mock.MagicMock,
        matching_bt_and_es: list[list[dict]],
    ) -> None:
        """Should return the expense source linked to one-offs."""
        # Arrange
        mock_get_data.side_effect = matching_bt_and_es

        # Act
        result = bank_button.BankButton._get_expense_source_id()

        # Assert
        assert result == _EXPENSE_SOURCE_ID

    @pytest.mark.parametrize(
        ("bt_data", "es_data"),
        [
            (
                [{"id": str(uuid.uuid4()), "name": "Expenses"}],
                None,
            ),
            (
                [{"id": _BT_ONE_OFFS_ID, "name": "One-offs"}],
                [],
            ),
            (
                [{"id": _BT_ONE_OFFS_ID, "name": "One-offs"}],
                [
                    {
                        "id": str(uuid.uuid4()),
                        "name": "Groceries",
                        "budget_tracker_ids": [str(uuid.uuid4())],
                    },
                ],
            ),
            (
                [{"id": _BT_ONE_OFFS_ID, "name": "One-offs"}],
                [
                    {
                        "id": str(uuid.uuid4()),
                        "name": "Misc",
                        "budget_tracker_ids": None,
                    },
                ],
            ),
        ],
        ids=[
            "no-one-offs-bt",
            "empty-expense-sources",
            "no-matching-es",
            "null-bt-ids",
        ],
    )
    @mock.patch.object(bank_button.data_client, "get_data")
    def test_returns_none_when_no_match(
        self,
        mock_get_data: mock.MagicMock,
        bt_data: list[dict],
        es_data: list[dict] | None,
    ) -> None:
        """Should return None when there is no valid match."""
        # Arrange
        if es_data is None:
            mock_get_data.return_value = bt_data
        else:
            mock_get_data.side_effect = [bt_data, es_data]

        # Act
        result = bank_button.BankButton._get_expense_source_id()

        # Assert
        assert result is None

    @mock.patch.object(bank_button.data_client, "get_data")
    def test_matches_among_multiple_expense_sources(
        self,
        mock_get_data: mock.MagicMock,
    ) -> None:
        """Should find the correct source when multiple expense sources exist."""
        # Arrange
        other_bt_id = str(uuid.uuid4())
        mock_get_data.side_effect = [
            [{"id": _BT_ONE_OFFS_ID, "name": "One-offs"}],
            [
                {
                    "id": str(uuid.uuid4()),
                    "name": "Groceries",
                    "budget_tracker_ids": [other_bt_id],
                },
                {
                    "id": _EXPENSE_SOURCE_ID,
                    "name": "One-Offs Source",
                    "budget_tracker_ids": [other_bt_id, _BT_ONE_OFFS_ID],
                },
            ],
        ]

        # Act
        result = bank_button.BankButton._get_expense_source_id()

        # Assert
        assert result == _EXPENSE_SOURCE_ID
