"""The SQL reconcile function against the Python use case, on the same data."""

import dataclasses
import datetime
import typing
import uuid

import pytest
import st_supabase_connection

from domain import entities
from driven_adapters.supabase import repository as supabase_repos
from driving_adapters import cache
from use_cases.reconcile_subscriptions import ReconcileSubscriptionsUseCase

_TODAY = datetime.date(2026, 11, 15)
_PAYMENTS = "payments"
_SUBSCRIPTIONS = "subscriptions"

type _Cadence = typing.Literal[
    "weekly",
    "monthly",
    "quarterly",
    "biannually",
    "yearly",
]


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


@dataclasses.dataclass(frozen=True)
class _Ledger:
    """The rows every scenario's payments hang off."""

    user_id: str
    bank_id: uuid.UUID
    joint_account_id: uuid.UUID
    joint_bank_id: uuid.UUID
    joint_source_id: uuid.UUID


@pytest.fixture(name="ledger")
def _ledger(
    connection: st_supabase_connection.SupabaseConnection,
    test_user_id: str,
) -> typing.Generator[_Ledger, None, None]:
    """Provide a user with a personal bank account and a joint account."""
    account = entities.JointAccountModel(name="Parity")
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

    yield _Ledger(test_user_id, bank.id, account.id, joint_bank.id, source.id)

    connection.table(_PAYMENTS).delete().eq("user_id", test_user_id).execute()
    connection.table(_SUBSCRIPTIONS).delete().eq("user_id", test_user_id).execute()
    connection.table("income_sources").delete().eq("id", str(source.id)).execute()
    connection.table("bank_accounts").delete().eq("user_id", test_user_id).execute()
    connection.table("joint_accounts").delete().eq("id", str(account.id)).execute()
    cache._get_data_cached.clear()


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
                name="Sub: Parity",
                expense=25.0,
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
                name="Sub: Parity",
                income=25.0,
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


@pytest.fixture(name="subscription_of")
def _subscription_of(
    connection: st_supabase_connection.SupabaseConnection,
    ledger: _Ledger,
) -> typing.Callable[[_Scenario], uuid.UUID]:
    """Provide a function writing a scenario's subscription, returning its id."""

    def subscription_of(scenario: _Scenario) -> uuid.UUID:
        subscription = entities.SubscriptionModel(
            user_id=ledger.user_id,
            name="Parity",
            amount=25.0,
            cadence=scenario.cadence,
            bank_account_id=ledger.bank_id,
            start_date=scenario.start,
            end_date=scenario.end,
            is_active=scenario.active,
            joint_income_source_id=ledger.joint_source_id
            if scenario.contribution
            else None,
            joint_bank_account_id=ledger.joint_bank_id
            if scenario.contribution
            else None,
        )
        connection.table(_SUBSCRIPTIONS).insert(
            subscription.model_dump(mode="json"),
        ).execute()
        return subscription.id

    return subscription_of


@pytest.fixture(name="run_python")
def _run_python(
    connection: st_supabase_connection.SupabaseConnection,
    ledger: _Ledger,
) -> typing.Callable[[], None]:
    """Provide a function running the Python use case as of ``_TODAY``."""

    def run_python() -> None:
        cache._get_data_cached.clear()
        cache_impl = cache.StreamlitCache()
        repo_args = (ledger.user_id, cache_impl, connection)
        ReconcileSubscriptionsUseCase(
            subscription_repo=supabase_repos.subscription_repository(
                *repo_args,
                entities.OwnershipType.PERSONAL,
            ),
            payment_repo=supabase_repos.payment_repository(
                *repo_args,
                entities.OwnershipType.PERSONAL,
            ),
            joint_payment_repo=supabase_repos.payment_repository(
                *repo_args,
                entities.OwnershipType.JOINT,
            ),
            today=_TODAY,
        ).execute()
        cache._get_data_cached.clear()

    return run_python


@pytest.fixture(name="run_sql")
def _run_sql(
    connection: st_supabase_connection.SupabaseConnection,
    ledger: _Ledger,
) -> typing.Callable[[], None]:
    """Provide a function running the SQL function as of ``_TODAY``."""

    def run_sql() -> None:
        connection.client.rpc(
            "reconcile_subscriptions",
            {
                "p_user_id": ledger.user_id,
                "p_ownership": "personal",
                "p_today": _TODAY.isoformat(),
            },
        ).execute()

    return run_sql


@pytest.fixture(name="outcome_of")
def _outcome_of(
    connection: st_supabase_connection.SupabaseConnection,
    ledger: _Ledger,
    seed: typing.Callable[[_Scenario, uuid.UUID], set[str]],
) -> typing.Callable[..., list[dict[str, object]]]:
    """Provide a function seeding a scenario, reconciling it, and returning its rows.

    New rows get new ids, so a row is compared by whether it was seeded and whether
    it is linked rather than by its id.
    """

    def outcome_of(
        scenario: _Scenario,
        subscription_id: uuid.UUID,
        run: typing.Callable[[], None],
    ) -> list[dict[str, object]]:
        written = seed(scenario, subscription_id)
        run()
        response = (
            connection.table(_PAYMENTS)
            .select("*")
            .eq("user_id", ledger.user_id)
            .eq("subscription_id", str(subscription_id))
            .execute()
        )
        rows = typing.cast("list[dict[str, object]]", response.data)
        connection.table(_PAYMENTS).delete().eq(
            "subscription_id",
            str(subscription_id),
        ).execute()
        compared = (
            "ownership_type",
            "joint_account_id",
            "payment_type",
            "name",
            "expense",
            "income",
            "payment_date",
            "checked",
            "bank_account_id",
            "category_id",
            "income_source_id",
        )
        return sorted(
            (
                {
                    **{column: row[column] for column in compared},
                    "seeded": row["id"] in written,
                    "linked": row["linked_payment_id"] is not None,
                }
                for row in rows
            ),
            key=lambda row: (str(row["payment_type"]), str(row["payment_date"])),
        )

    return outcome_of


@pytest.mark.parametrize("scenario", _SCENARIOS.values(), ids=_SCENARIOS.keys())
def test_sql_books_what_python_books(
    scenario: _Scenario,
    subscription_of: typing.Callable[[_Scenario], uuid.UUID],
    outcome_of: typing.Callable[..., list[dict[str, object]]],
    run_python: typing.Callable[[], None],
    run_sql: typing.Callable[[], None],
) -> None:
    # Arrange
    subscription_id = subscription_of(scenario)

    # Act
    from_python = outcome_of(scenario, subscription_id, run_python)
    from_sql = outcome_of(scenario, subscription_id, run_sql)

    # Assert
    expense_dates = tuple(
        row["payment_date"] for row in from_sql if row["payment_type"] == "expense"
    )
    assert (from_sql, expense_dates) == (
        from_python,
        tuple(date.isoformat() for date in scenario.expected),
    )
