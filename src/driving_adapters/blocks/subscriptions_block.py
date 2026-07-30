"""Subscriptions block for managing recurring payments.

Two grids over the one ``subscriptions`` table: the ordinary subscriptions, and
— on the personal page, for a user who has a joint account — the joint
contributions, the standing orders that book a linked pair of payments each
cadence. They are separated because the joint columns would be null for almost
every ordinary row and are meaningless on the joint page's copy of the grid.

The split is client-side, over the one personal slice already fetched: each grid
carries its own ``row_predicate`` and its own widget-key prefix. A filtered read
would be Path B and would need its own cache key.
"""

import dataclasses
import datetime
from typing import TYPE_CHECKING

import pandas as pd
import streamlit as st

from driving_adapters import lookups
from driving_adapters.components.dfes import grid
from driving_adapters.models import frontend_models

if TYPE_CHECKING:
    import uuid
    from collections.abc import Callable

    from domain import read_models
    from driving_adapters.components.dfes import data_source as data_source_mod

_TABLE_NAME = "subscriptions"
_CONTRIBUTIONS_KEY_PREFIX = "joint_contributions"

_CADENCE_OPTIONS = ["weekly", "monthly", "quarterly", "biannually", "yearly"]

_TODAY = datetime.datetime.now(tz=datetime.UTC).date().isoformat()

_SAMPLE_DATA = pd.DataFrame(
    {
        "name": ["Example Subscription"],
        "amount": [0.0],
        "cadence": ["monthly"],
        "bank_account_id": ["example bank account"],
        "expense_source_id": ["example expense source"],
        "start_date": [_TODAY],
        "end_date": [None],
        "is_active": [True],
        "monthly_cost": [0.0],
    },
)

_CONTRIBUTIONS_SAMPLE_DATA = pd.DataFrame(
    {
        "name": ["Example Contribution"],
        "amount": [0.0],
        "cadence": ["monthly"],
        "bank_account_id": ["example bank account"],
        "joint_bank_account_id": ["example joint bank account"],
        "joint_income_source_id": ["example joint income source"],
        "start_date": [_TODAY],
        "end_date": [None],
        "is_active": [True],
        "monthly_cost": [0.0],
    },
)


@dataclasses.dataclass(frozen=True)
class JointContributionLookups:
    """The joint-side values the contributions grid needs to offer and derive.

    Built only for a user who belongs to a joint account; its absence is what
    tells the block there is no contributions tab to show.
    """

    bank_account_map: dict[str, str]
    """``{id: name}`` of the joint bank accounts the money arrives in."""

    income_source_map: dict[str, str]
    """``{id: name}`` of the joint income sources to book the arrival against."""

    expense_source_id: "uuid.UUID | None" = None
    """The hidden personal "Joint" expense source the expense leg is booked to.

    Derived, never chosen, so it is merged into a new row rather than offered as
    a column.
    """


def _is_contribution(row: "read_models.SubscriptionView") -> bool:
    """Whether a row is a joint contribution rather than a plain subscription."""
    return row.joint_income_source_id is not None


def _is_plain_subscription(row: "read_models.SubscriptionView") -> bool:
    """Whether a row belongs on the ordinary subscriptions grid."""
    return row.joint_income_source_id is None


def _core_columns(
    bank_account_label: str,
    bank_account_ids: list[str],
    get_bank_account_name: "Callable[[str | float], str]",
) -> list[frontend_models.DFEColumnConfig]:
    """Build the columns every subscription grid opens with."""
    return [
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
        _selectbox_column(
            "bank_account_id",
            bank_account_label,
            "Select a bank account",
            bank_account_ids,
            get_bank_account_name,
        ),
    ]


def _schedule_columns() -> list[frontend_models.DFEColumnConfig]:
    """Build the columns every subscription grid closes with."""
    return [
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
            required=False,
        ),
        frontend_models.DFEColumnConfig(
            column_name="is_active",
            column_config=st.column_config.CheckboxColumn("Active"),
            button_label="Active",
            input_widget=st.checkbox,
            input_kwargs={"value": True},
        ),
        frontend_models.DFEColumnConfig(
            editable=False,
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
    ]


def _selectbox_column(
    column_name: str,
    label: str,
    help_text: str,
    ids: list[str],
    get_name: "Callable[[str | float], str]",
) -> frontend_models.DFEColumnConfig:
    """Build a foreign-key selectbox column shown as its target's name."""
    return frontend_models.DFEColumnConfig(
        column_name=column_name,
        column_config=st.column_config.SelectboxColumn(
            label,
            help=help_text,
            options=ids,
            format_func=get_name,
        ),
        button_label=label,
        input_widget=st.selectbox,
        input_kwargs={
            "options": ids,
            "index": None,
            "format_func": get_name,
        },
        format_func=get_name,
    )


def _build_config(
    data_source: "data_source_mod.GridDataSource",
    bank_account_map: dict[str, str],
    expense_source_map: dict[str, str],
    *,
    split_out_contributions: bool,
) -> frontend_models.DFEConfig:
    """Build the grid config for the ordinary subscriptions.

    The contributions are held back only when there is a tab showing them:
    without one, a leftover contribution row (a user who has since left their
    joint account) would be invisible and so unmanageable.
    """
    return frontend_models.DFEConfig(
        source=frontend_models.GridSource(
            write_table=_TABLE_NAME,
            data_source=data_source,
            row_predicate=_is_plain_subscription if split_out_contributions else None,
        ),
        display=frontend_models.GridDisplay(
            columns=[
                *_core_columns(
                    "Bank Account",
                    list(bank_account_map.keys()),
                    lookups.make_name_formatter(
                        bank_account_map,
                        "Unknown Bank Account",
                    ),
                ),
                _selectbox_column(
                    "expense_source_id",
                    "Expense Source",
                    "Select an expense source",
                    list(expense_source_map.keys()),
                    lookups.make_name_formatter(
                        expense_source_map,
                        "Unknown Expense Source",
                    ),
                ),
                *_schedule_columns(),
            ],
            sample_data=_SAMPLE_DATA,
        ),
    )


def _build_contributions_config(
    data_source: "data_source_mod.GridDataSource",
    bank_account_map: dict[str, str],
    joint: JointContributionLookups,
) -> frontend_models.DFEConfig:
    """Build the grid config for the joint contributions.

    No expense-source column: a contribution's personal leg is always booked
    against the hidden "Joint" source, so it is merged into a new row rather
    than chosen. The grid shares the ``subscriptions`` table with the ordinary
    grid, so it takes its own widget-key prefix.
    """
    return frontend_models.DFEConfig(
        source=frontend_models.GridSource(
            write_table=_TABLE_NAME,
            key_prefix_override=_CONTRIBUTIONS_KEY_PREFIX,
            data_source=data_source,
            row_predicate=_is_contribution,
            extra_row_values={"expense_source_id": joint.expense_source_id},
        ),
        display=frontend_models.GridDisplay(
            columns=[
                *_core_columns(
                    "From (personal)",
                    list(bank_account_map.keys()),
                    lookups.make_name_formatter(
                        bank_account_map,
                        "Unknown Bank Account",
                    ),
                ),
                _selectbox_column(
                    "joint_bank_account_id",
                    "To (joint)",
                    "The joint bank account the money arrives in",
                    list(joint.bank_account_map.keys()),
                    lookups.make_name_formatter(
                        joint.bank_account_map,
                        "Unknown Joint Bank Account",
                    ),
                ),
                _selectbox_column(
                    "joint_income_source_id",
                    "Joint Income Source",
                    "What the arriving money is booked against",
                    list(joint.income_source_map.keys()),
                    lookups.make_name_formatter(
                        joint.income_source_map,
                        "Unknown Joint Income Source",
                    ),
                ),
                *_schedule_columns(),
            ],
            sample_data=_CONTRIBUTIONS_SAMPLE_DATA,
        ),
    )


def _configs(
    data_source: "data_source_mod.GridDataSource",
    bank_account_map: dict[str, str],
    expense_source_map: dict[str, str],
    joint: JointContributionLookups | None,
) -> list[frontend_models.DFEConfig]:
    """Build every grid config this block renders, in tab order."""
    configs = [
        _build_config(
            data_source,
            bank_account_map,
            expense_source_map,
            split_out_contributions=joint is not None,
        ),
    ]
    if joint is not None:
        configs.append(
            _build_contributions_config(data_source, bank_account_map, joint),
        )
    return configs


def commit(
    data_source: "data_source_mod.GridDataSource",
    bank_account_map: dict[str, str],
    expense_source_map: dict[str, str],
    joint: JointContributionLookups | None = None,
) -> None:
    """Apply any pending backend updates for this block."""
    for config in _configs(data_source, bank_account_map, expense_source_map, joint):
        grid.commit(config)


def render(
    data_source: "data_source_mod.GridDataSource",
    bank_account_map: dict[str, str],
    expense_source_map: dict[str, str],
    joint: JointContributionLookups | None = None,
) -> None:
    """Render the subscriptions block, with a contributions tab when there is one."""
    configs = _configs(data_source, bank_account_map, expense_source_map, joint)
    if len(configs) == 1:
        grid.render(configs[0])
        return

    tabs = st.tabs(["Subscriptions", "Joint Contributions"])
    for tab, config in zip(tabs, configs, strict=True):
        with tab:
            grid.render(config)
