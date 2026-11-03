"""The ``reconcile_subscriptions`` database function, against the testing database.

The scenarios call the function directly so they can fix its date. The tests at
the bottom go through the repository, for what the function cannot show: that a
run reaches the database and that the next read sees what it booked.
"""

import concurrent.futures
import dataclasses
import datetime
import typing
import uuid

import postgrest
import pytest
import st_supabase_connection

from domain import entities
from driven_adapters.supabase import repository as supabase_repos
from driving_adapters import cache

_TODAY = datetime.date(2026, 11, 15)
_PAYMENTS = "payments"
_SUBSCRIPTIONS = "subscriptions"
_FUNCTION = "reconcile_subscriptions"
_PERSONAL = "personal"
_JOINT = "joint"
_AMOUNT = 25.0
_NAME = "Reconciled"
_BOOKED_NAME = f"Sub: {_NAME}"

type _Cadence = typing.Literal[
    "weekly",
    "monthly",
    "quarterly",
    "biannually",
    "yearly",
]
type _Row = dict[str, typing.Any]


def _day(year: int, month: int, day: int) -> datetime.date:
    return datetime.date(year, month, day)


@dataclasses.dataclass(frozen=True)
class _Scenario:
    """A subscription and its payments, and the expense dates it should end with."""

    start: datetime.date
    expected: tuple[datetime.date, ...]
    cadence: _Cadence = "monthly"
    end: datetime.date | None = None
    active: bool = True
    expenses: tuple[datetime.date, ...] = ()
    contribution: bool = False
    incomes: tuple[datetime.date, ...] = ()
    """The expense dates that already have a joint income pointing back at them."""
    linked_forward: bool = False
    """Whether those expenses already point forward at their income."""


_SUBSCRIPTION_SCENARIOS = {
    "monthly_from_the_past": _Scenario(_day(2026, 1, 10), (_day(2026, 12, 10),)),
    "due_today": _Scenario(_day(2026, 11, 15), (_day(2026, 11, 15),)),
    "starts_in_the_future": _Scenario(_day(2026, 12, 1), (_day(2026, 12, 1),)),
    "weekly": _Scenario(_day(2026, 11, 2), (_day(2026, 11, 16),), cadence="weekly"),
    "quarterly": _Scenario(
        _day(2026, 2, 20),
        (_day(2026, 11, 20),),
        cadence="quarterly",
    ),
    "biannually": _Scenario(
        _day(2026, 1, 5),
        (_day(2027, 1, 5),),
        cadence="biannually",
    ),
    "yearly": _Scenario(_day(2025, 12, 1), (_day(2026, 12, 1),), cadence="yearly"),
    "month_end_drifts_after_february": _Scenario(
        _day(2026, 1, 31),
        (_day(2026, 11, 28),),
    ),
    "leap_day_drifts": _Scenario(
        _day(2024, 2, 29),
        (_day(2027, 2, 28),),
        cadence="yearly",
    ),
    "inactive_loses_future_keeps_past": _Scenario(
        _day(2026, 1, 1),
        (_day(2026, 10, 1),),
        active=False,
        expenses=(_day(2026, 10, 1), _day(2026, 12, 1)),
    ),
    "expired_loses_future_keeps_past": _Scenario(
        _day(2026, 1, 1),
        (_day(2026, 10, 1),),
        end=_day(2026, 11, 1),
        expenses=(_day(2026, 10, 1), _day(2026, 12, 1)),
    ),
    "payment_past_the_end_goes_and_the_next_is_booked": _Scenario(
        _day(2026, 1, 10),
        (_day(2026, 12, 10),),
        end=_day(2027, 1, 31),
        expenses=(_day(2027, 2, 10),),
    ),
    "ends_before_the_next_date": _Scenario(
        _day(2026, 1, 20),
        (),
        end=_day(2026, 11, 16),
    ),
    "future_payment_left_alone": _Scenario(
        _day(2026, 1, 10),
        (_day(2026, 12, 10),),
        expenses=(_day(2026, 12, 10),),
    ),
    "payment_today_counts_as_future": _Scenario(
        _day(2026, 1, 15),
        (_day(2026, 11, 15),),
        expenses=(_day(2026, 11, 15),),
    ),
    "payment_just_inside_the_cycle_settles_it": _Scenario(
        _day(2026, 1, 20),
        (_day(2026, 11, 5), _day(2026, 12, 20)),
        expenses=(_day(2026, 11, 5),),
    ),
    "payment_on_the_cycle_boundary_does_not": _Scenario(
        _day(2026, 1, 20),
        (_day(2026, 11, 4), _day(2026, 11, 20)),
        expenses=(_day(2026, 11, 4),),
    ),
    "settled_cycle_with_the_following_past_the_end": _Scenario(
        _day(2026, 1, 20),
        (_day(2026, 11, 12),),
        end=_day(2026, 12, 1),
        expenses=(_day(2026, 11, 12),),
    ),
}

_CONTRIBUTION_SCENARIOS = {
    "books_a_new_pair": _Scenario(
        _day(2026, 1, 10),
        (_day(2026, 12, 10),),
        contribution=True,
    ),
    "inactive_removes_both_legs": _Scenario(
        _day(2026, 1, 10),
        (),
        active=False,
        contribution=True,
        expenses=(_day(2026, 12, 10),),
        incomes=(_day(2026, 12, 10),),
        linked_forward=True,
    ),
    "inactive_keeps_a_past_pair": _Scenario(
        _day(2026, 1, 10),
        (_day(2026, 10, 10),),
        active=False,
        contribution=True,
        expenses=(_day(2026, 10, 10),),
        incomes=(_day(2026, 10, 10),),
        linked_forward=True,
    ),
    "repairs_a_missing_income": _Scenario(
        _day(2026, 1, 10),
        (_day(2026, 12, 10),),
        contribution=True,
        expenses=(_day(2026, 12, 10),),
    ),
    "repairs_a_missing_forward_link": _Scenario(
        _day(2026, 1, 10),
        (_day(2026, 12, 10),),
        contribution=True,
        expenses=(_day(2026, 12, 10),),
        incomes=(_day(2026, 12, 10),),
    ),
    "leaves_a_whole_pair_alone": _Scenario(
        _day(2026, 1, 10),
        (_day(2026, 12, 10),),
        contribution=True,
        expenses=(_day(2026, 12, 10),),
        incomes=(_day(2026, 12, 10),),
        linked_forward=True,
    ),
}

_SCENARIOS = _SUBSCRIPTION_SCENARIOS | _CONTRIBUTION_SCENARIOS

_ORDINARY = _Scenario(_day(2026, 1, 10), (_day(2026, 12, 10),))
_CONTRIBUTION = _CONTRIBUTION_SCENARIOS["books_a_new_pair"]


@dataclasses.dataclass(frozen=True)
class _Ledger:
    """The rows every scenario's payments hang off."""

    user_id: str
    other_user_id: str
    """A second user, who belongs to no joint account."""
    bank_id: uuid.UUID
    category_id: uuid.UUID
    joint_account_id: uuid.UUID
    joint_bank_id: uuid.UUID
    joint_source_id: uuid.UUID


def _of_type(rows: list[_Row], payment_type: str) -> list[_Row]:
    return [row for row in rows if row["payment_type"] == payment_type]


def _expense_dates(rows: list[_Row]) -> list[str]:
    return sorted(row["payment_date"] for row in _of_type(rows, "expense"))


@pytest.fixture(name="ledger")
def _ledger(
    connection: st_supabase_connection.SupabaseConnection,
    test_user_id: str,
) -> typing.Generator[_Ledger, None, None]:
    """Provide a user with a personal bank account and a joint account."""
    cache._get_data_cached.clear()
    other_user_id = f"{test_user_id}-other"
    users = [test_user_id, other_user_id]
    account = entities.JointAccountModel(name="Reconcile")
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
    category = entities.CategoryModel(user_id=test_user_id, name="Subscriptions")
    connection.table("categories").insert(category.model_dump(mode="json")).execute()

    yield _Ledger(
        test_user_id,
        other_user_id,
        bank.id,
        category.id,
        account.id,
        joint_bank.id,
        source.id,
    )

    connection.table(_PAYMENTS).delete().in_("user_id", users).execute()
    connection.table(_SUBSCRIPTIONS).delete().in_("user_id", users).execute()
    connection.table("categories").delete().eq("id", str(category.id)).execute()
    connection.table("income_sources").delete().eq("id", str(source.id)).execute()
    connection.table("bank_accounts").delete().eq("user_id", test_user_id).execute()
    connection.table("joint_accounts").delete().eq("id", str(account.id)).execute()
    cache._get_data_cached.clear()


@pytest.fixture(name="subscription_of")
def _subscription_of(
    connection: st_supabase_connection.SupabaseConnection,
    ledger: _Ledger,
) -> typing.Callable[..., uuid.UUID]:
    """Provide a function writing a scenario's subscription, returning its id.

    Keyword arguments override the subscription's fields, so a test can give it to
    another user or to the joint half.
    """

    def subscription_of(scenario: _Scenario, **overrides: object) -> uuid.UUID:
        contribution_fields: dict[str, object] = (
            {
                "joint_income_source_id": ledger.joint_source_id,
                "joint_bank_account_id": ledger.joint_bank_id,
            }
            if scenario.contribution
            else {}
        )
        fields: dict[str, typing.Any] = {
            "user_id": ledger.user_id,
            **contribution_fields,
            **overrides,
        }
        subscription = entities.SubscriptionModel(
            name=_NAME,
            amount=_AMOUNT,
            cadence=scenario.cadence,
            bank_account_id=ledger.bank_id,
            category_id=ledger.category_id,
            start_date=scenario.start,
            end_date=scenario.end,
            is_active=scenario.active,
            **fields,
        )
        connection.table(_SUBSCRIPTIONS).insert(
            subscription.model_dump(mode="json"),
        ).execute()
        return subscription.id

    return subscription_of


@pytest.fixture(name="seed")
def _seed(
    connection: st_supabase_connection.SupabaseConnection,
    ledger: _Ledger,
) -> typing.Callable[[_Scenario, uuid.UUID], set[str]]:
    """Provide a function writing a scenario's payments, returning the ids written."""

    def seed(scenario: _Scenario, subscription_id: uuid.UUID) -> set[str]:
        written: set[str] = set()
        for date in scenario.expenses:
            expense = entities.ExpensePaymentModel(
                user_id=ledger.user_id,
                name=_BOOKED_NAME,
                expense=_AMOUNT,
                payment_date=date,
                bank_account_id=ledger.bank_id,
                subscription_id=subscription_id,
            )
            connection.table(_PAYMENTS).insert(
                expense.model_dump(mode="json"),
            ).execute()
            written.add(str(expense.id))
            if date not in scenario.incomes:
                continue
            income = entities.IncomePaymentModel(
                user_id=ledger.user_id,
                name=_BOOKED_NAME,
                income=_AMOUNT,
                payment_date=date,
                bank_account_id=ledger.joint_bank_id,
                income_source_id=ledger.joint_source_id,
                subscription_id=subscription_id,
                linked_payment_id=expense.id,
                ownership_type=entities.OwnershipType.JOINT,
                joint_account_id=ledger.joint_account_id,
            )
            connection.table(_PAYMENTS).insert(income.model_dump(mode="json")).execute()
            written.add(str(income.id))
            if scenario.linked_forward:
                connection.table(_PAYMENTS).update(
                    {"linked_payment_id": str(income.id)},
                ).eq("id", str(expense.id)).execute()
        return written

    return seed


@pytest.fixture(name="reconcile")
def _reconcile(
    connection: st_supabase_connection.SupabaseConnection,
    ledger: _Ledger,
) -> typing.Callable[..., None]:
    """Provide a function calling the database function as of ``_TODAY``."""

    def reconcile(ownership: str = _PERSONAL, user_id: str | None = None) -> None:
        connection.client.rpc(
            _FUNCTION,
            {
                "p_user_id": user_id or ledger.user_id,
                "p_ownership": ownership,
                "p_today": _TODAY.isoformat(),
            },
        ).execute()

    return reconcile


@pytest.fixture(name="payments_of")
def _payments_of(
    connection: st_supabase_connection.SupabaseConnection,
) -> typing.Callable[[uuid.UUID], list[_Row]]:
    """Provide a function returning a subscription's payments, of either half."""

    def payments_of(subscription_id: uuid.UUID) -> list[_Row]:
        response = (
            connection.table(_PAYMENTS)
            .select("*")
            .eq("subscription_id", str(subscription_id))
            .execute()
        )
        return typing.cast("list[_Row]", response.data)

    return payments_of


def _row_summary(row: _Row) -> _Row:
    """Return a booked row without the columns a test cannot know in advance."""
    generated = ("id", "linked_payment_id", "_created_at", "subscription_id")
    return {column: row[column] for column in row if column not in generated}


@pytest.mark.parametrize("scenario", _SCENARIOS.values(), ids=_SCENARIOS.keys())
def test_ends_with_the_expected_expense_dates(
    scenario: _Scenario,
    subscription_of: typing.Callable[..., uuid.UUID],
    seed: typing.Callable[[_Scenario, uuid.UUID], set[str]],
    reconcile: typing.Callable[..., None],
    payments_of: typing.Callable[[uuid.UUID], list[_Row]],
) -> None:
    # Arrange
    subscription_id = subscription_of(scenario)
    seed(scenario, subscription_id)

    # Act
    reconcile()

    # Assert
    assert _expense_dates(payments_of(subscription_id)) == sorted(
        date.isoformat() for date in scenario.expected
    )


@pytest.mark.parametrize("scenario", _SCENARIOS.values(), ids=_SCENARIOS.keys())
def test_a_kept_expense_is_the_seeded_row_not_a_new_one(
    scenario: _Scenario,
    subscription_of: typing.Callable[..., uuid.UUID],
    seed: typing.Callable[[_Scenario, uuid.UUID], set[str]],
    reconcile: typing.Callable[..., None],
    payments_of: typing.Callable[[uuid.UUID], list[_Row]],
) -> None:
    # Arrange
    subscription_id = subscription_of(scenario)
    seeded = seed(scenario, subscription_id)

    # Act
    reconcile()

    # Assert
    kept = [row for row in payments_of(subscription_id) if row["id"] in seeded]
    assert _expense_dates(kept) == sorted(
        date.isoformat() for date in set(scenario.expected) & set(scenario.expenses)
    )


@pytest.mark.parametrize(
    "scenario",
    _CONTRIBUTION_SCENARIOS.values(),
    ids=_CONTRIBUTION_SCENARIOS.keys(),
)
def test_every_contribution_expense_ends_cross_linked_to_its_income(
    scenario: _Scenario,
    subscription_of: typing.Callable[..., uuid.UUID],
    seed: typing.Callable[[_Scenario, uuid.UUID], set[str]],
    reconcile: typing.Callable[..., None],
    payments_of: typing.Callable[[uuid.UUID], list[_Row]],
) -> None:
    # Arrange
    subscription_id = subscription_of(scenario)
    seed(scenario, subscription_id)

    # Act
    reconcile()

    # Assert
    rows = payments_of(subscription_id)
    expenses = _of_type(rows, "expense")
    incomes = {row["id"]: row for row in _of_type(rows, "income")}
    linked = [incomes.get(expense["linked_payment_id"]) for expense in expenses]
    assert all(
        [
            len(incomes) == len(expenses),
            *(
                income is not None
                and income["linked_payment_id"] == expense["id"]
                and income["payment_date"] == expense["payment_date"]
                for expense, income in zip(expenses, linked, strict=True)
            ),
        ],
    )


@pytest.mark.parametrize(
    "scenario",
    _SUBSCRIPTION_SCENARIOS.values(),
    ids=_SUBSCRIPTION_SCENARIOS.keys(),
)
def test_an_ordinary_subscription_books_no_income(
    scenario: _Scenario,
    subscription_of: typing.Callable[..., uuid.UUID],
    seed: typing.Callable[[_Scenario, uuid.UUID], set[str]],
    reconcile: typing.Callable[..., None],
    payments_of: typing.Callable[[uuid.UUID], list[_Row]],
) -> None:
    # Arrange
    subscription_id = subscription_of(scenario)
    seed(scenario, subscription_id)

    # Act
    reconcile()

    # Assert
    assert _of_type(payments_of(subscription_id), "income") == []


def test_a_booked_expense_takes_its_fields_from_the_subscription(
    ledger: _Ledger,
    subscription_of: typing.Callable[..., uuid.UUID],
    reconcile: typing.Callable[..., None],
    payments_of: typing.Callable[[uuid.UUID], list[_Row]],
) -> None:
    # Arrange
    subscription_id = subscription_of(_ORDINARY)

    # Act
    reconcile()

    # Assert
    [expense] = payments_of(subscription_id)
    assert _row_summary(expense) == {
        "user_id": ledger.user_id,
        "name": _BOOKED_NAME,
        "income": 0,
        "expense": _AMOUNT,
        "payment_date": _ORDINARY.expected[0].isoformat(),
        "checked": False,
        "bank_account_id": str(ledger.bank_id),
        "payment_type": "expense",
        "category_id": str(ledger.category_id),
        "income_source_id": None,
        "ownership_type": _PERSONAL,
        "joint_account_id": None,
    }


def test_a_booked_income_leg_lands_in_the_joint_books(
    ledger: _Ledger,
    subscription_of: typing.Callable[..., uuid.UUID],
    reconcile: typing.Callable[..., None],
    payments_of: typing.Callable[[uuid.UUID], list[_Row]],
) -> None:
    # Arrange
    subscription_id = subscription_of(_CONTRIBUTION)

    # Act
    reconcile()

    # Assert
    [income] = _of_type(payments_of(subscription_id), "income")
    assert _row_summary(income) == {
        "user_id": ledger.user_id,
        "name": _BOOKED_NAME,
        "income": _AMOUNT,
        "expense": 0,
        "payment_date": _CONTRIBUTION.expected[0].isoformat(),
        "checked": False,
        "bank_account_id": str(ledger.joint_bank_id),
        "payment_type": "income",
        "category_id": None,
        "income_source_id": str(ledger.joint_source_id),
        "ownership_type": _JOINT,
        "joint_account_id": str(ledger.joint_account_id),
    }


@pytest.mark.parametrize(
    "scenario",
    [_ORDINARY, _CONTRIBUTION],
    ids=["ordinary", "contribution"],
)
def test_a_second_run_changes_nothing(
    scenario: _Scenario,
    subscription_of: typing.Callable[..., uuid.UUID],
    reconcile: typing.Callable[..., None],
    payments_of: typing.Callable[[uuid.UUID], list[_Row]],
) -> None:
    # Arrange
    subscription_id = subscription_of(scenario)
    reconcile()
    before = {row["id"] for row in payments_of(subscription_id)}

    # Act
    reconcile()

    # Assert
    assert {row["id"] for row in payments_of(subscription_id)} == before


def test_runs_at_the_same_moment_book_one_payment(
    subscription_of: typing.Callable[..., uuid.UUID],
    reconcile: typing.Callable[..., None],
    payments_of: typing.Callable[[uuid.UUID], list[_Row]],
) -> None:
    # Arrange
    subscription_id = subscription_of(_ORDINARY)

    # Act
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for future in [pool.submit(reconcile) for _ in range(4)]:
            future.result()

    # Assert
    assert len(payments_of(subscription_id)) == 1


def test_a_contribution_with_no_joint_account_is_left_alone(
    ledger: _Ledger,
    subscription_of: typing.Callable[..., uuid.UUID],
    reconcile: typing.Callable[..., None],
    payments_of: typing.Callable[[uuid.UUID], list[_Row]],
) -> None:
    # Arrange
    subscription_id = subscription_of(_CONTRIBUTION, user_id=ledger.other_user_id)

    # Act
    reconcile(user_id=ledger.other_user_id)

    # Assert
    assert payments_of(subscription_id) == []


def test_no_joint_account_does_not_stop_the_other_subscriptions(
    ledger: _Ledger,
    subscription_of: typing.Callable[..., uuid.UUID],
    reconcile: typing.Callable[..., None],
    payments_of: typing.Callable[[uuid.UUID], list[_Row]],
) -> None:
    # Arrange
    subscription_of(_CONTRIBUTION, user_id=ledger.other_user_id)
    ordinary_id = subscription_of(_ORDINARY, user_id=ledger.other_user_id)

    # Act
    reconcile(user_id=ledger.other_user_id)

    # Assert
    assert _expense_dates(payments_of(ordinary_id)) == [
        _ORDINARY.expected[0].isoformat(),
    ]


def test_a_joint_run_with_no_joint_account_does_nothing(
    ledger: _Ledger,
    subscription_of: typing.Callable[..., uuid.UUID],
    reconcile: typing.Callable[..., None],
    payments_of: typing.Callable[[uuid.UUID], list[_Row]],
) -> None:
    # Arrange
    subscription_id = subscription_of(_ORDINARY, user_id=ledger.other_user_id)

    # Act
    reconcile(_JOINT, user_id=ledger.other_user_id)

    # Assert
    assert payments_of(subscription_id) == []


def test_a_joint_run_books_a_joint_expense(
    ledger: _Ledger,
    subscription_of: typing.Callable[..., uuid.UUID],
    reconcile: typing.Callable[..., None],
    payments_of: typing.Callable[[uuid.UUID], list[_Row]],
) -> None:
    # Arrange
    subscription_id = subscription_of(
        _ORDINARY,
        ownership_type=entities.OwnershipType.JOINT,
        joint_account_id=ledger.joint_account_id,
    )

    # Act
    reconcile(_JOINT)

    # Assert
    [expense] = payments_of(subscription_id)
    assert (expense["ownership_type"], expense["joint_account_id"]) == (
        _JOINT,
        str(ledger.joint_account_id),
    )


def test_a_joint_run_reaches_a_co_members_subscription(
    ledger: _Ledger,
    subscription_of: typing.Callable[..., uuid.UUID],
    reconcile: typing.Callable[..., None],
    payments_of: typing.Callable[[uuid.UUID], list[_Row]],
) -> None:
    # Arrange
    subscription_id = subscription_of(
        _ORDINARY,
        user_id=ledger.other_user_id,
        ownership_type=entities.OwnershipType.JOINT,
        joint_account_id=ledger.joint_account_id,
    )

    # Act
    reconcile(_JOINT)

    # Assert
    assert len(payments_of(subscription_id)) == 1


def test_a_joint_run_leaves_a_personal_contribution_alone(
    subscription_of: typing.Callable[..., uuid.UUID],
    reconcile: typing.Callable[..., None],
    payments_of: typing.Callable[[uuid.UUID], list[_Row]],
) -> None:
    # Arrange
    subscription_id = subscription_of(_CONTRIBUTION)

    # Act
    reconcile(_JOINT)

    # Assert
    assert payments_of(subscription_id) == []


def test_a_personal_run_leaves_a_joint_subscription_alone(
    ledger: _Ledger,
    subscription_of: typing.Callable[..., uuid.UUID],
    reconcile: typing.Callable[..., None],
    payments_of: typing.Callable[[uuid.UUID], list[_Row]],
) -> None:
    # Arrange
    subscription_id = subscription_of(
        _ORDINARY,
        ownership_type=entities.OwnershipType.JOINT,
        joint_account_id=ledger.joint_account_id,
    )

    # Act
    reconcile()

    # Assert
    assert payments_of(subscription_id) == []


def test_a_personal_run_leaves_another_users_subscription_alone(
    ledger: _Ledger,
    subscription_of: typing.Callable[..., uuid.UUID],
    reconcile: typing.Callable[..., None],
    payments_of: typing.Callable[[uuid.UUID], list[_Row]],
) -> None:
    # Arrange
    subscription_id = subscription_of(_ORDINARY, user_id=ledger.other_user_id)

    # Act
    reconcile()

    # Assert
    assert payments_of(subscription_id) == []


def test_an_unknown_ownership_is_rejected(
    reconcile: typing.Callable[..., None],
) -> None:
    # Act / Assert
    with pytest.raises(postgrest.APIError, match="Unknown ownership"):
        reconcile("shared")


@pytest.fixture(name="repo_of")
def _repo_of(
    connection: st_supabase_connection.SupabaseConnection,
    ledger: _Ledger,
) -> typing.Callable[..., typing.Any]:
    """Provide a function building a repository on the real cache."""

    def repo_of(
        factory: typing.Callable[..., typing.Any],
        ownership: entities.OwnershipType = entities.OwnershipType.PERSONAL,
    ) -> typing.Any:  # noqa: ANN401 - each factory returns its own repository type
        return factory(ledger.user_id, cache.StreamlitCache(), connection, ownership)

    return repo_of


@pytest.fixture(name="due_today")
def _due_today() -> _Scenario:
    """Provide a subscription due on the function's own default date."""
    today = datetime.datetime.now(tz=datetime.UTC).date()
    return _Scenario(today, (today,))


def test_a_reconcile_shows_up_in_a_warm_payments_read(
    due_today: _Scenario,
    subscription_of: typing.Callable[..., uuid.UUID],
    repo_of: typing.Callable[..., typing.Any],
) -> None:
    # Arrange
    subscription_of(due_today)
    payments = repo_of(supabase_repos.payment_repository)
    payments.get_all()

    # Act
    repo_of(supabase_repos.subscription_repository).reconcile_subscriptions()

    # Assert
    assert [payment.payment_date for payment in payments.get_all()] == [
        due_today.start,
    ]


def test_a_personal_reconcile_shows_up_in_a_warm_joint_payments_read(
    due_today: _Scenario,
    subscription_of: typing.Callable[..., uuid.UUID],
    repo_of: typing.Callable[..., typing.Any],
) -> None:
    # Arrange
    subscription_of(dataclasses.replace(due_today, contribution=True))
    joint_payments = repo_of(
        supabase_repos.payment_repository,
        entities.OwnershipType.JOINT,
    )
    joint_payments.get_all()

    # Act
    repo_of(supabase_repos.subscription_repository).reconcile_subscriptions()

    # Assert
    assert [payment.income for payment in joint_payments.get_all()] == [_AMOUNT]
