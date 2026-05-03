"""Subscriptions block for managing recurring payments."""

import datetime
from collections.abc import Callable

import pandas as pd
import streamlit as st
from dateutil import relativedelta

from libs import data_client
from libs.dfes import base_dfe
from libs.dfes import constants as dfe_constants
from libs.models import backend_models, frontend_models

_TABLE_NAME = dfe_constants.TableNames.SUBSCRIPTIONS.value
_VIEW_NAME = dfe_constants.TableNames.SUBSCRIPTIONS_VIEW.value
_TABLES_TO_CLEAR = [
    dfe_constants.TableNames.SUBSCRIPTIONS,
    dfe_constants.TableNames.SUBSCRIPTIONS_VIEW,
    dfe_constants.TableNames.PAYMENTS,
    dfe_constants.TableNames.BANK_ACCOUNTS_VIEW,
    dfe_constants.TableNames.EXPENSE_SOURCES_VIEW,
]

_CADENCE_OPTIONS = ["weekly", "fortnightly", "monthly", "quarterly", "yearly"]

_SAMPLE_DATA = pd.DataFrame(
    {
        "name": ["Example Subscription"],
        "amount": [0.0],
        "cadence": ["monthly"],
        "bank_account_id": ["example bank account"],
        "expense_source_id": ["example expense source"],
        "start_date": [datetime.datetime.now(tz=datetime.UTC).date().isoformat()],
        "end_date": [None],
        "is_active": [True],
        "monthly_cost": [0.0],
    },
)

_CADENCE_DELTAS = {
    "weekly": relativedelta.relativedelta(weeks=1),
    "fortnightly": relativedelta.relativedelta(weeks=2),
    "monthly": relativedelta.relativedelta(months=1),
    "quarterly": relativedelta.relativedelta(months=3),
    "yearly": relativedelta.relativedelta(years=1),
}


def _build_dfe(
    bank_account_ids: list[str],
    get_bank_account_name: Callable,
    expense_source_ids: list[str],
    get_expense_source_name: Callable,
) -> base_dfe.DFE:
    """Build the DFE for the subscriptions block."""
    return base_dfe.DFE(
        config=frontend_models.DFEConfig(
            table_names=frontend_models.DFETableNameConfig(
                write_table=_TABLE_NAME,
                read_table=_VIEW_NAME,
            ),
            backend_model=backend_models.SubscriptionModel,
            configs=[
                frontend_models.DFEColumnConfig(
                    column_name="name",
                    column_config=st.column_config.TextColumn(
                        "Name",
                        required=True,
                    ),
                    button_label="Name",
                    input_widget=st.text_input,
                    input_kwargs={"value": None},
                ),
                frontend_models.DFEColumnConfig(
                    column_name="amount",
                    column_config=st.column_config.NumberColumn(
                        "Amount",
                        format="£%.2f",
                    ),
                    button_label="Amount",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.2f"},
                ),
                frontend_models.DFEColumnConfig(
                    column_name="cadence",
                    column_config=st.column_config.SelectboxColumn(
                        "Cadence",
                        options=_CADENCE_OPTIONS,
                    ),
                    button_label="Cadence",
                    input_widget=st.selectbox,
                    input_kwargs={
                        "options": _CADENCE_OPTIONS,
                        "index": 2,
                    },
                ),
                frontend_models.DFEColumnConfig(
                    column_name="bank_account_id",
                    column_config=st.column_config.SelectboxColumn(
                        "Bank Account",
                        help="Select a bank account",
                        options=bank_account_ids,
                        format_func=get_bank_account_name,
                    ),
                    button_label="Bank Account",
                    input_widget=st.selectbox,
                    input_kwargs={
                        "options": bank_account_ids,
                        "index": None,
                        "format_func": get_bank_account_name,
                    },
                    format_func=get_bank_account_name,
                ),
                frontend_models.DFEColumnConfig(
                    column_name="expense_source_id",
                    column_config=st.column_config.SelectboxColumn(
                        "Expense Source",
                        help="Select an expense source",
                        options=expense_source_ids,
                        format_func=get_expense_source_name,
                    ),
                    button_label="Expense Source",
                    input_widget=st.selectbox,
                    input_kwargs={
                        "options": expense_source_ids,
                        "index": None,
                        "format_func": get_expense_source_name,
                    },
                    format_func=get_expense_source_name,
                ),
                frontend_models.DFEColumnConfig(
                    column_name="start_date",
                    column_config=st.column_config.DateColumn(
                        "Start Date",
                        format="localized",
                    ),
                    button_label="Start Date",
                    input_widget=st.date_input,
                ),
                frontend_models.DFEColumnConfig(
                    column_name="end_date",
                    column_config=st.column_config.DateColumn(
                        "End Date",
                        format="localized",
                    ),
                    button_label="End Date",
                    input_widget=st.date_input,
                    input_kwargs={"value": None},
                ),
                frontend_models.DFEColumnConfig(
                    column_name="is_active",
                    column_config=st.column_config.CheckboxColumn("Active"),
                    button_label="Active",
                    input_widget=st.checkbox,
                    input_kwargs={"value": True},
                ),
                frontend_models.DFEReadOnlyColumnConfig(
                    column_name="monthly_cost",
                    column_config=st.column_config.NumberColumn(
                        "Monthly Cost",
                        format="£%.2f",
                        disabled=True,
                    ),
                    button_label="Monthly Cost",
                    input_widget=st.number_input,
                    input_kwargs={"value": None, "format": "%.2f"},
                ),
            ],
            sample_data=_SAMPLE_DATA,
            tables_to_clear=_TABLES_TO_CLEAR,
        ),
    )


def _get_next_payment_dates(
    start_date: datetime.date,
    cadence: str,
    end_date: datetime.date | None,
    horizon: datetime.date,
) -> list[datetime.date]:
    """Compute payment dates from start_date up to horizon (or end_date).

    Only returns dates that are today or in the future.
    """
    delta = _CADENCE_DELTAS.get(cadence)
    if delta is None:
        return []

    cutoff = min(end_date, horizon) if end_date else horizon
    today = datetime.datetime.now(tz=datetime.UTC).date()
    dates: list[datetime.date] = []
    current = start_date
    while current <= cutoff:
        if current >= today:
            dates.append(current)
        current += delta
    return dates


def generate_subscription_payments() -> None:
    """Generate missing payment entries for active subscriptions (Option C).

    Looks one month ahead from today. For each active subscription, computes
    expected payment dates and inserts any that don't already exist.
    """
    subscriptions = data_client.get_data(
        table_name=_TABLE_NAME,
        query_string="*",
    )
    if not subscriptions:
        return

    validated_subs = [
        backend_models.SubscriptionModel.model_validate(sub) for sub in subscriptions
    ]

    existing_payments = data_client.get_data(
        table_name="payments",
        query_string="subscription_id,payment_date",
    )
    existing_set: set[tuple[str, str]] = {
        (str(p["subscription_id"]), str(p["payment_date"]))
        for p in existing_payments
        if p.get("subscription_id")
    }

    horizon = datetime.datetime.now(
        tz=datetime.UTC,
    ).date() + relativedelta.relativedelta(months=1)

    new_payments: list[dict] = []
    for sub in validated_subs:
        if not sub.is_active:
            continue

        sub_id = str(sub.id)
        dates = _get_next_payment_dates(
            sub.start_date,
            sub.cadence,
            sub.end_date,
            horizon,
        )

        for pay_date in dates:
            key = (sub_id, str(pay_date))
            if key not in existing_set:
                payment_model = backend_models.ExpensePaymentModel(
                    user_id=sub.user_id,
                    name=f"Sub: {sub.name}",
                    expense=sub.amount,
                    payment_date=pay_date,
                    bank_account_id=sub.bank_account_id,
                    expense_source_id=sub.expense_source_id,
                    subscription_id=sub.id,
                )
                new_payments.append(
                    payment_model.model_dump(mode="json"),
                )
                existing_set.add(key)

    if new_payments:
        data_client.CONN.table(dfe_constants.TableNames.PAYMENTS.value).insert(
            new_payments,
        ).execute()
        data_client.invalidate_table_cache(dfe_constants.TableNames.PAYMENTS.value)
        data_client.invalidate_table_cache(
            dfe_constants.TableNames.BANK_ACCOUNTS_VIEW.value,
        )


def commit() -> None:
    """Apply any pending backend updates for this block."""
    data_client.commit(
        table_name=_TABLE_NAME,
        tables_to_clear=_TABLES_TO_CLEAR,
        key_prefix=_TABLE_NAME,
    )


def render() -> None:
    """Render the subscriptions block."""
    bank_accounts_data = data_client.get_data(
        table_name="bank_accounts",
        query_string="*",
    )
    bank_account_map: dict[str, str] = {
        str(ba["id"]): str(ba["name"]) for ba in bank_accounts_data
    }
    bank_account_ids = list(bank_account_map.keys())

    def get_bank_account_name(ba_id: str | float) -> str:
        return bank_account_map.get(str(ba_id), "Unknown Bank Account")

    expense_sources = data_client.get_data(
        table_name="expense_sources",
        query_string="*",
    )
    expense_source_map: dict[str, str] = {
        str(es["id"]): str(es["name"]) for es in expense_sources
    }
    expense_source_ids = list(expense_source_map.keys())

    def get_expense_source_name(es_id: str | float) -> str:
        return expense_source_map.get(str(es_id), "Unknown Expense Source")

    dfe = _build_dfe(
        bank_account_ids,
        get_bank_account_name,
        expense_source_ids,
        get_expense_source_name,
    )
    dfe.load_input_data()
    data_added, filters_changed = dfe.render_buttons()
    dfe.refresh(filters_changed=filters_changed, data_added=data_added)
    dfe.render_editor()
