"""Unit tests for domain view read models."""

import uuid

import pydantic
import pytest

from domain import read_models

USER_ID = "user-abc"


def _base(name: str = "Test") -> dict:
    return {"id": str(uuid.uuid4()), "user_id": USER_ID, "name": name}


# ---------------------------------------------------------------------------
# BankAccountView
# ---------------------------------------------------------------------------

CURRENT_BALANCE = 350.75


def test_bank_account_view_parses_current_balance():
    # Arrange
    row = {
        **_base("Monzo"),
        "starting_balance": 100.0,
        "current_balance": CURRENT_BALANCE,
    }

    # Act
    model = read_models.BankAccountView.model_validate(row)

    # Assert
    assert model.current_balance == CURRENT_BALANCE


def test_bank_account_view_is_frozen():
    # Arrange
    model = read_models.BankAccountView.model_validate(
        {**_base(), "starting_balance": 0.0, "current_balance": 0.0},
    )

    # Act / Assert
    with pytest.raises(pydantic.ValidationError, match="Instance is frozen"):
        model.current_balance = 99.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# BudgetTrackerView
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("field", "value"),
    [
        pytest.param("current_month", 120.0, id="current_month"),
        pytest.param("remaining", 80.0, id="remaining"),
        pytest.param("progress", 60.0, id="progress"),
        pytest.param("split", 25.0, id="split"),
    ],
)
def test_budget_tracker_view_parses_computed_column(field: str, value: float):
    # Arrange
    row = {
        **_base("Expenses"),
        "total_budget": 200.0,
        "current_month": 120.0,
        "remaining": 80.0,
        "progress": 60.0,
        "split": 25.0,
    }

    # Act
    model = read_models.BudgetTrackerView.model_validate(row)

    # Assert
    assert getattr(model, field) == value


def test_budget_tracker_view_is_frozen():
    # Arrange
    row = {**_base("Expenses"), "total_budget": 0.0}
    model = read_models.BudgetTrackerView.model_validate(row)

    # Act / Assert
    with pytest.raises(pydantic.ValidationError, match="Instance is frozen"):
        model.progress = 50.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ExpenseSourceView
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("field", "value"),
    [
        pytest.param("current_month", 50.0, id="current_month"),
        pytest.param("remaining", 150.0, id="remaining"),
        pytest.param("progress", 25.0, id="progress"),
        pytest.param("split", 10.0, id="split"),
    ],
)
def test_expense_source_view_parses_computed_column(field: str, value: float):
    # Arrange
    row = {
        **_base("Groceries"),
        "budget": 200.0,
        "budget_tracker_ids": None,
        "current_month": 50.0,
        "remaining": 150.0,
        "progress": 25.0,
        "split": 10.0,
    }

    # Act
    model = read_models.ExpenseSourceView.model_validate(row)

    # Assert
    assert getattr(model, field) == value


def test_expense_source_view_budget_tracker_ids_parses_as_list_of_uuids():
    # Arrange
    bt_id = uuid.uuid4()
    row = {**_base(), "budget_tracker_ids": [str(bt_id)]}

    # Act
    model = read_models.ExpenseSourceView.model_validate(row)

    # Assert
    assert model.budget_tracker_ids == [bt_id]


# ---------------------------------------------------------------------------
# IncomeSourceView
# ---------------------------------------------------------------------------

INCOME_CURRENT_MONTH = 3000.0


def test_income_source_view_parses_current_month():
    # Arrange
    row = {
        **_base("Salary"),
        "budget_tracker_ids": [],
        "current_month": INCOME_CURRENT_MONTH,
    }

    # Act
    model = read_models.IncomeSourceView.model_validate(row)

    # Assert
    assert model.current_month == INCOME_CURRENT_MONTH


def test_income_source_view_is_frozen():
    # Arrange
    model = read_models.IncomeSourceView.model_validate(
        {**_base(), "budget_tracker_ids": []},
    )

    # Act / Assert
    with pytest.raises(pydantic.ValidationError, match="Instance is frozen"):
        model.current_month = 999.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# SubscriptionView
# ---------------------------------------------------------------------------

MONTHLY_COST = 12.99


def test_subscription_view_parses_monthly_cost():
    # Arrange
    row = {
        **_base("Netflix"),
        "amount": MONTHLY_COST,
        "cadence": "monthly",
        "bank_account_id": str(uuid.uuid4()),
        "start_date": "2024-01-01",
        "is_active": True,
        "monthly_cost": MONTHLY_COST,
    }

    # Act
    model = read_models.SubscriptionView.model_validate(row)

    # Assert
    assert model.monthly_cost == MONTHLY_COST


def test_subscription_view_quarterly_cadence_is_preserved():
    # Arrange
    row = {
        **_base("Gym"),
        "amount": 90.0,
        "cadence": "quarterly",
        "bank_account_id": str(uuid.uuid4()),
        "start_date": "2024-01-01",
        "is_active": True,
        "monthly_cost": 30.0,
    }

    # Act
    model = read_models.SubscriptionView.model_validate(row)

    # Assert
    assert model.cadence == "quarterly"


# ---------------------------------------------------------------------------
# OneOffView
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("field", "value"),
    [
        pytest.param("remaining", 700.0, id="remaining"),
        pytest.param("progress", 30.0, id="progress"),
        pytest.param("split", 40.0, id="split"),
    ],
)
def test_one_off_view_parses_computed_column(field: str, value: float):
    # Arrange
    row = {
        **_base("Holiday"),
        "cost": 1000.0,
        "current_month": 50.0,
        "banked": 300.0,
        "budget_tracker_id": None,
        "remaining": 700.0,
        "progress": 30.0,
        "split": 40.0,
    }

    # Act
    model = read_models.OneOffView.model_validate(row)

    # Assert
    assert getattr(model, field) == value


ONE_OFF_COST = 5000.0
ONE_OFF_BANKED = 1000.0
ONE_OFF_CURRENT_MONTH = 200.0


def test_one_off_view_write_fields_also_survive_validation():
    # Arrange
    row = {
        **_base("Car"),
        "cost": ONE_OFF_COST,
        "current_month": ONE_OFF_CURRENT_MONTH,
        "banked": ONE_OFF_BANKED,
        "budget_tracker_id": None,
        "remaining": 4000.0,
        "progress": 20.0,
        "split": 15.0,
    }

    # Act
    model = read_models.OneOffView.model_validate(row)

    # Assert
    assert all([
        model.cost == ONE_OFF_COST,
        model.banked == ONE_OFF_BANKED,
        model.current_month == ONE_OFF_CURRENT_MONTH,
    ])


def test_one_off_view_is_frozen():
    # Arrange
    row = {**_base(), "cost": 0.0, "current_month": 0.0, "banked": 0.0}
    model = read_models.OneOffView.model_validate(row)

    # Act / Assert
    with pytest.raises(pydantic.ValidationError, match="Instance is frozen"):
        model.remaining = 100.0  # type: ignore[misc]
