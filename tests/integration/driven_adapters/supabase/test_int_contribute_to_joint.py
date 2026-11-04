"""The ``contribute_to_joint`` database function, against the testing database."""

import dataclasses
import datetime
import typing
import uuid

import postgrest
import pytest
import st_supabase_connection

from domain import entities

_PAYMENTS = "payments"
_FUNCTION = "contribute_to_joint"
_AMOUNT = 25.0
_DATE = datetime.date(2026, 11, 15)
_ACCOUNT_NAME = "Household"

type _Row = dict[str, typing.Any]


@dataclasses.dataclass(frozen=True)
class _Ledger:
    """What a contribution needs to already exist."""

    user_id: str
    bank_id: uuid.UUID
    category_id: uuid.UUID
    joint_account_id: uuid.UUID
    joint_bank_id: uuid.UUID
    joint_source_id: uuid.UUID


@pytest.fixture(name="ledger")
def _ledger(
    connection: st_supabase_connection.SupabaseConnection,
    test_user_id: str,
) -> typing.Generator[_Ledger, None, None]:
    """Provide a member of a joint account, with a "Joint" tracker and both accounts."""
    account = entities.JointAccountModel(name=_ACCOUNT_NAME)
    connection.table("joint_accounts").insert(account.model_dump(mode="json")).execute()
    member = entities.JointAccountMemberModel(
        joint_account_id=account.id,
        user_id=test_user_id,
    )
    connection.table("joint_account_members").insert(
        member.model_dump(mode="json"),
    ).execute()
    joint_fields: dict[str, typing.Any] = {
        "user_id": test_user_id,
        "ownership_type": entities.OwnershipType.JOINT,
        "joint_account_id": account.id,
    }
    bank = entities.BankAccountModel(user_id=test_user_id, name="Personal")
    joint_bank = entities.BankAccountModel(name="Joint", **joint_fields)
    connection.table("bank_accounts").insert(
        [bank.model_dump(mode="json"), joint_bank.model_dump(mode="json")],
    ).execute()
    source = entities.IncomeSourceModel(name="Contributions", **joint_fields)
    connection.table("income_sources").insert(source.model_dump(mode="json")).execute()
    category = entities.CategoryModel(
        user_id=test_user_id,
        name=entities.BudgetTrackerName.JOINT,
    )
    connection.table("categories").insert(category.model_dump(mode="json")).execute()

    yield _Ledger(
        test_user_id,
        bank.id,
        category.id,
        account.id,
        joint_bank.id,
        source.id,
    )

    connection.table(_PAYMENTS).delete().eq("user_id", test_user_id).execute()
    connection.table("categories").delete().eq("id", str(category.id)).execute()
    connection.table("income_sources").delete().eq("id", str(source.id)).execute()
    connection.table("bank_accounts").delete().eq("user_id", test_user_id).execute()
    connection.table("joint_accounts").delete().eq("id", str(account.id)).execute()


@pytest.fixture(name="contribute")
def _contribute(
    connection: st_supabase_connection.SupabaseConnection,
    ledger: _Ledger,
) -> typing.Callable[..., None]:
    """Provide a call of the function, for a test to override one argument of."""

    def contribute(**overrides: object) -> None:
        connection.client.rpc(
            _FUNCTION,
            {
                "p_user_id": ledger.user_id,
                "p_amount": _AMOUNT,
                "p_from_bank_account_id": str(ledger.bank_id),
                "p_to_bank_account_id": str(ledger.joint_bank_id),
                "p_income_source_id": str(ledger.joint_source_id),
                "p_payment_date": _DATE.isoformat(),
                **overrides,
            },
        ).execute()

    return contribute


@pytest.fixture(name="payments")
def _payments(
    connection: st_supabase_connection.SupabaseConnection,
    ledger: _Ledger,
) -> typing.Callable[[], list[_Row]]:
    """Provide a read of every payment the user wrote."""

    def payments() -> list[_Row]:
        response = (
            connection.table(_PAYMENTS)
            .select("*")
            .eq("user_id", ledger.user_id)
            .execute()
        )
        return typing.cast("list[_Row]", response.data)

    return payments


def _leg(rows: list[_Row], payment_type: str) -> _Row:
    return next(row for row in rows if row["payment_type"] == payment_type)


def test_books_the_personal_expense(
    ledger: _Ledger,
    contribute: typing.Callable[..., None],
    payments: typing.Callable[[], list[_Row]],
) -> None:
    # Arrange
    fields = (
        "name",
        "expense",
        "income",
        "payment_date",
        "bank_account_id",
        "category_id",
        "ownership_type",
        "joint_account_id",
    )

    # Act
    contribute()

    # Assert
    expense = _leg(payments(), "expense")
    assert {field: expense[field] for field in fields} == {
        "name": f"Joint: {_ACCOUNT_NAME}",
        "expense": _AMOUNT,
        "income": 0,
        "payment_date": _DATE.isoformat(),
        "bank_account_id": str(ledger.bank_id),
        "category_id": str(ledger.category_id),
        "ownership_type": "personal",
        "joint_account_id": None,
    }


def test_books_the_joint_income(
    ledger: _Ledger,
    contribute: typing.Callable[..., None],
    payments: typing.Callable[[], list[_Row]],
) -> None:
    # Arrange
    fields = (
        "name",
        "expense",
        "income",
        "payment_date",
        "bank_account_id",
        "income_source_id",
        "ownership_type",
        "joint_account_id",
    )

    # Act
    contribute()

    # Assert
    income = _leg(payments(), "income")
    assert {field: income[field] for field in fields} == {
        "name": f"Joint: {_ACCOUNT_NAME}",
        "expense": 0,
        "income": _AMOUNT,
        "payment_date": _DATE.isoformat(),
        "bank_account_id": str(ledger.joint_bank_id),
        "income_source_id": str(ledger.joint_source_id),
        "ownership_type": "joint",
        "joint_account_id": str(ledger.joint_account_id),
    }


def test_each_leg_points_at_the_other(
    contribute: typing.Callable[..., None],
    payments: typing.Callable[[], list[_Row]],
) -> None:
    # Arrange
    # Act
    contribute()

    # Assert
    rows = payments()
    expense, income = _leg(rows, "expense"), _leg(rows, "income")
    assert all(
        [
            expense["linked_payment_id"] == income["id"],
            income["linked_payment_id"] == expense["id"],
        ],
    )


@pytest.mark.parametrize("amount", [0, -5])
def test_a_contribution_of_nothing_is_rejected(
    contribute: typing.Callable[..., None],
    amount: float,
) -> None:
    # Arrange
    # Act
    # Assert
    with pytest.raises(postgrest.APIError, match="more than zero"):
        contribute(p_amount=amount)


def test_a_rejected_contribution_writes_nothing(
    contribute: typing.Callable[..., None],
    payments: typing.Callable[[], list[_Row]],
) -> None:
    # Arrange
    # A destination that doesn't exist fails the second leg, after the first is written.
    missing = str(uuid.uuid4())

    # Act
    with pytest.raises(postgrest.APIError):
        contribute(p_to_bank_account_id=missing)

    # Assert
    assert payments() == []


def test_a_user_in_no_joint_account_is_rejected(
    contribute: typing.Callable[..., None],
    test_user_id: str,
) -> None:
    # Arrange
    outsider = f"{test_user_id}-outsider"

    # Act
    # Assert
    with pytest.raises(postgrest.APIError, match="not a member"):
        contribute(p_user_id=outsider)


def test_a_user_with_no_joint_tracker_is_rejected(
    connection: st_supabase_connection.SupabaseConnection,
    ledger: _Ledger,
    contribute: typing.Callable[..., None],
) -> None:
    # Arrange
    connection.table("categories").delete().eq("id", str(ledger.category_id)).execute()

    # Act
    # Assert
    with pytest.raises(postgrest.APIError, match="no Joint budget tracker"):
        contribute()
