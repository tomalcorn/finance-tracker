"""Unit tests for the auth module."""

import typing
import uuid
from unittest import mock

import pytest

from libs import auth, data_client


class TestSeedDefaultBudgetTrackers:
    """Tests for _seed_default_budget_trackers."""

    _BT_IDS: typing.ClassVar[list[str]] = [str(uuid.uuid4()) for _ in range(4)]
    _BT_ROWS_ALL: typing.ClassVar[list[dict[str, object]]] = [
        {"id": _BT_IDS[0], "name": "Expenses"},
        {"id": _BT_IDS[1], "name": "Joint"},
        {"id": _BT_IDS[2], "name": "One-offs"},
        {"id": _BT_IDS[3], "name": "Savings"},
    ]

    @pytest.fixture
    def _mock_conn(self) -> typing.Generator[mock.MagicMock, None, None]:
        with mock.patch.object(data_client, "CONN") as conn:
            yield conn

    @staticmethod
    def _get_data_side_effect(
        bt_rows: list[dict[str, object]],
        es_rows: list[dict[str, object]] | None = None,
    ) -> typing.Callable[..., list[dict[str, object]]]:
        """Return a side_effect for get_data that serves different tables."""
        if es_rows is None:
            es_rows = []

        def _side_effect(
            table_name: str,
            query_string: str,
            **_: object,
        ) -> list[dict[str, object]]:
            if table_name == "budget_tracker":
                if "id" in query_string:
                    return bt_rows
                return [{"name": r["name"]} for r in bt_rows]
            if table_name == "expense_sources":
                return es_rows
            return []

        return _side_effect

    @pytest.mark.usefixtures("_mock_conn")
    def test_inserts_all_four_bt_when_none_exist(
        self,
    ) -> None:
        # First call returns empty (no BTs), re-fetch after insert returns all.
        call_count = 0

        def _side_effect(
            table_name: str,
            query_string: str,  # noqa: ARG001
            **_: object,
        ) -> list[dict[str, object]]:
            nonlocal call_count
            if table_name == "budget_tracker":
                call_count += 1
                if call_count <= 1:
                    return []
                return self._BT_ROWS_ALL
            return []

        with mock.patch.object(data_client, "get_data", side_effect=_side_effect):
            auth._seed_default_budget_trackers("auth0|user1")

        conn = typing.cast("mock.MagicMock", data_client.CONN)
        bt_call = conn.table("budget_tracker").upsert.call_args
        inserted = bt_call[0][0]
        names = {row["name"] for row in inserted}
        assert names == {"Expenses", "Joint", "One-offs", "Savings"}

    @pytest.mark.usefixtures("_mock_conn")
    def test_seeds_hidden_expense_sources(
        self,
    ) -> None:
        side_effect = self._get_data_side_effect(self._BT_ROWS_ALL, es_rows=[])
        with mock.patch.object(data_client, "get_data", side_effect=side_effect):
            auth._seed_default_budget_trackers("auth0|user1")

        conn = typing.cast("mock.MagicMock", data_client.CONN)
        conn.table("budget_tracker").upsert.assert_not_called()
        es_call = conn.table("expense_sources").insert.call_args
        inserted = es_call[0][0]
        names = {row["name"] for row in inserted}
        assert names == {"Joint", "One-offs", "Savings"}
        assert all(row["user_id"] == "auth0|user1" for row in inserted)

    @pytest.mark.usefixtures("_mock_conn")
    def test_skips_existing_expense_sources(
        self,
    ) -> None:
        existing_es: list[dict[str, object]] = [
            {"budget_tracker_ids": [self._BT_IDS[1], self._BT_IDS[3]]},
        ]
        side_effect = self._get_data_side_effect(
            self._BT_ROWS_ALL,
            es_rows=existing_es,
        )
        with mock.patch.object(data_client, "get_data", side_effect=side_effect):
            auth._seed_default_budget_trackers("auth0|user1")

        conn = typing.cast("mock.MagicMock", data_client.CONN)
        es_call = conn.table("expense_sources").insert.call_args
        inserted = es_call[0][0]
        names = {row["name"] for row in inserted}
        assert names == {"One-offs"}

    @pytest.mark.usefixtures("_mock_conn")
    def test_no_inserts_when_fully_seeded(
        self,
    ) -> None:
        existing_es: list[dict[str, object]] = [
            {"budget_tracker_ids": [self._BT_IDS[1], self._BT_IDS[2], self._BT_IDS[3]]},
        ]
        side_effect = self._get_data_side_effect(
            self._BT_ROWS_ALL,
            es_rows=existing_es,
        )
        with mock.patch.object(data_client, "get_data", side_effect=side_effect):
            auth._seed_default_budget_trackers("auth0|user1")

        conn = typing.cast("mock.MagicMock", data_client.CONN)
        conn.table("budget_tracker").upsert.assert_not_called()
        conn.table("expense_sources").insert.assert_not_called()
