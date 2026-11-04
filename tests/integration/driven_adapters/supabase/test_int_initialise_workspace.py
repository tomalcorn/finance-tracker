"""The ``initialise_workspace`` database function, against the testing database."""

import concurrent.futures
import dataclasses
import typing
import uuid

import postgrest
import pytest
import st_supabase_connection

from domain import entities

_FUNCTION = "initialise_workspace"
_CATEGORIES = "categories"
_SETTINGS = "user_settings"
_PERSONAL = "personal"
_JOINT = "joint"
_CHOSEN_PERIOD = "previous_month"

type _Row = dict[str, typing.Any]


@dataclasses.dataclass(frozen=True)
class _Ledger:
    """A user who may belong to a joint account, and its id if they do."""

    user_id: str
    joint_account_id: uuid.UUID


@pytest.fixture(name="ledger")
def _ledger(
    connection: st_supabase_connection.SupabaseConnection,
    test_user_id: str,
) -> typing.Generator[_Ledger, None, None]:
    """Provide a user in a joint account, with neither half set up."""
    user_id = f"{test_user_id}-workspace"
    outsider = f"{user_id}-outsider"
    account = entities.JointAccountModel(name="Workspace")
    connection.table("joint_accounts").insert(account.model_dump(mode="json")).execute()
    member = entities.JointAccountMemberModel(
        joint_account_id=account.id,
        user_id=user_id,
    )
    connection.table("joint_account_members").insert(
        member.model_dump(mode="json"),
    ).execute()

    yield _Ledger(user_id, account.id)

    for table in (_CATEGORIES, _SETTINGS):
        connection.table(table).delete().in_("user_id", [user_id, outsider]).execute()
    connection.table("joint_accounts").delete().eq("id", str(account.id)).execute()


@pytest.fixture(name="initialise")
def _initialise(
    connection: st_supabase_connection.SupabaseConnection,
    ledger: _Ledger,
) -> typing.Callable[..., None]:
    """Provide a call of the function."""

    def initialise(ownership: str = _PERSONAL, user_id: str | None = None) -> None:
        connection.client.rpc(
            _FUNCTION,
            {"p_user_id": user_id or ledger.user_id, "p_ownership": ownership},
        ).execute()

    return initialise


@pytest.fixture(name="rows")
def _rows(
    connection: st_supabase_connection.SupabaseConnection,
    ledger: _Ledger,
) -> typing.Callable[..., list[_Row]]:
    """Provide a read of one table's rows for one half."""

    def rows(
        table: str,
        ownership: str = _PERSONAL,
        user_id: str | None = None,
    ) -> list[_Row]:
        response = (
            connection.table(table)
            .select("*")
            .eq("user_id", user_id or ledger.user_id)
            .eq("ownership_type", ownership)
            .execute()
        )
        return typing.cast("list[_Row]", response.data)

    return rows


def test_a_personal_run_seeds_every_tracker(
    initialise: typing.Callable[..., None],
    rows: typing.Callable[..., list[_Row]],
) -> None:
    # Arrange
    # Act
    initialise()

    # Assert
    assert {row["name"] for row in rows(_CATEGORIES)} == set(entities.BudgetTrackerName)


def test_a_joint_run_seeds_every_tracker_but_joint(
    initialise: typing.Callable[..., None],
    rows: typing.Callable[..., list[_Row]],
) -> None:
    # Arrange
    expected = set(entities.BudgetTrackerName) - {entities.BudgetTrackerName.JOINT}

    # Act
    initialise(_JOINT)

    # Assert
    assert {row["name"] for row in rows(_CATEGORIES, _JOINT)} == expected


def test_joint_trackers_belong_to_the_account(
    ledger: _Ledger,
    initialise: typing.Callable[..., None],
    rows: typing.Callable[..., list[_Row]],
) -> None:
    # Arrange
    # Act
    initialise(_JOINT)

    # Assert
    assert {row["joint_account_id"] for row in rows(_CATEGORIES, _JOINT)} == {
        str(ledger.joint_account_id),
    }


@pytest.mark.parametrize("ownership", [_PERSONAL, _JOINT])
def test_seeded_trackers_are_roots_with_no_budget(
    initialise: typing.Callable[..., None],
    rows: typing.Callable[..., list[_Row]],
    ownership: str,
) -> None:
    # Arrange
    # Act
    initialise(ownership)

    # Assert
    assert all(
        row["parent_id"] is None and row["budget"] == 0 and row["accrual"] == "monthly"
        for row in rows(_CATEGORIES, ownership)
    )


@pytest.mark.parametrize("ownership", [_PERSONAL, _JOINT])
def test_seeds_one_settings_row_at_the_default(
    initialise: typing.Callable[..., None],
    rows: typing.Callable[..., list[_Row]],
    ownership: str,
) -> None:
    # Arrange
    # Act
    initialise(ownership)

    # Assert
    assert [row["income_roll_up_period"] for row in rows(_SETTINGS, ownership)] == [
        "current_month",
    ]


@pytest.mark.parametrize(
    ("ownership", "table"),
    [
        (_PERSONAL, _CATEGORIES),
        (_PERSONAL, _SETTINGS),
        (_JOINT, _CATEGORIES),
        (_JOINT, _SETTINGS),
    ],
)
def test_a_second_run_changes_nothing(
    initialise: typing.Callable[..., None],
    rows: typing.Callable[..., list[_Row]],
    ownership: str,
    table: str,
) -> None:
    # Arrange
    initialise(ownership)
    before = rows(table, ownership)

    # Act
    initialise(ownership)

    # Assert
    assert sorted(row["id"] for row in rows(table, ownership)) == sorted(
        row["id"] for row in before
    )


def test_runs_at_the_same_moment_seed_each_tracker_once(
    initialise: typing.Callable[..., None],
    rows: typing.Callable[..., list[_Row]],
) -> None:
    # Arrange
    # Act
    with concurrent.futures.ThreadPoolExecutor() as pool:
        for future in [pool.submit(initialise) for _ in range(4)]:
            future.result()

    # Assert
    assert len(rows(_CATEGORIES)) == len(entities.BudgetTrackerName)


def test_a_chosen_period_survives_another_run(
    connection: st_supabase_connection.SupabaseConnection,
    ledger: _Ledger,
    initialise: typing.Callable[..., None],
    rows: typing.Callable[..., list[_Row]],
) -> None:
    # Arrange
    initialise()
    connection.table(_SETTINGS).update({"income_roll_up_period": _CHOSEN_PERIOD}).eq(
        "user_id",
        ledger.user_id,
    ).execute()

    # Act
    initialise()

    # Assert
    assert rows(_SETTINGS)[0]["income_roll_up_period"] == _CHOSEN_PERIOD


def test_a_missing_tracker_is_filled_in(
    connection: st_supabase_connection.SupabaseConnection,
    ledger: _Ledger,
    initialise: typing.Callable[..., None],
    rows: typing.Callable[..., list[_Row]],
) -> None:
    # Arrange
    initialise()
    connection.table(_CATEGORIES).delete().eq("user_id", ledger.user_id).eq(
        "name",
        entities.BudgetTrackerName.SAVINGS,
    ).execute()

    # Act
    initialise()

    # Assert
    assert {row["name"] for row in rows(_CATEGORIES)} == set(entities.BudgetTrackerName)


def test_a_joint_run_with_no_joint_account_seeds_nothing(
    ledger: _Ledger,
    initialise: typing.Callable[..., None],
    rows: typing.Callable[..., list[_Row]],
) -> None:
    # Arrange
    outsider = f"{ledger.user_id}-outsider"

    # Act
    initialise(_JOINT, outsider)

    # Assert
    assert rows(_CATEGORIES, _JOINT, outsider) == []


def test_an_unknown_ownership_is_rejected(
    initialise: typing.Callable[..., None],
) -> None:
    # Arrange
    # Act
    # Assert
    with pytest.raises(postgrest.APIError, match="Unknown ownership"):
        initialise("shared")
