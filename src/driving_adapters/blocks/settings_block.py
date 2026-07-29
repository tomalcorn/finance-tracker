"""Block for the settings section.

One ``render`` call configures one half of the finances. The settings page calls
it twice — once with a personal use case, once with a joint one — so the two
halves are independent all the way down: separate rows, separate cache entries,
separate controls.

A change is written as soon as the selection differs from what is stored; there
is no explicit Save. The use case guards the no-op, so reselecting the current
value writes nothing.
"""

import logging

import streamlit as st

from domain import entities
from driving_adapters import ss_keys
from use_cases import errors as use_case_errors
from use_cases import manage_user_settings

logger = logging.getLogger(__name__)

_PERIOD_LABELS: dict[entities.IncomeRollUpPeriod, str] = {
    entities.IncomeRollUpPeriod.CURRENT_MONTH: "This month",
    entities.IncomeRollUpPeriod.PREVIOUS_MONTH: "Last month",
}

_INCOME_HELP = (
    "The budget tracker's Split is each tracker's budget as a share of the "
    "income feeding it. This chooses which month's income that is. Spending is "
    "always totalled over the current month."
)


def _period_label(period: entities.IncomeRollUpPeriod | str) -> str:
    """Return the selectbox label for a period."""
    return _PERIOD_LABELS[entities.IncomeRollUpPeriod(period)]


def _save(
    use_case: "manage_user_settings.ManageUserSettingsUseCase",
    period: entities.IncomeRollUpPeriod,
    ownership: entities.OwnershipType,
) -> bool:
    """Persist the chosen period, reporting whether it was written."""
    try:
        use_case.set_income_roll_up_period(period)
    except use_case_errors.UserSettingsError:
        logger.exception("Failed to save %s income roll-up period.", ownership)
        st.error("Could not save that setting. Please try again or contact support.")
        return False
    st.session_state[ss_keys.SSKeys.SETTINGS_TOAST] = (
        f"{ownership.value.capitalize()} income now rolls up over "
        f"{_period_label(period).lower()}."
    )
    return True


def flush_toast() -> None:
    """Show the confirmation left by the previous run, if there is one.

    A save is followed by a rerun, which would cut a toast raised during it
    short, so the message waits in session state until the page is rebuilt.
    """
    message = st.session_state.pop(ss_keys.SSKeys.SETTINGS_TOAST, None)
    if message:
        st.toast(str(message), icon=":material/check_circle:")


def render(
    use_case: "manage_user_settings.ManageUserSettingsUseCase",
    ownership: entities.OwnershipType,
) -> None:
    """Render the settings for one half of the finances.

    Args:
        use_case: Loads and saves the settings of the half being configured.
        ownership: Which half that is. Names the controls, so the two rendered
            sections cannot share widget state.

    Raises:
        UserSettingsReadError: The settings could not be read. Left to the
            page's error boundary, like every other read a page makes.

    """
    settings = use_case.load()
    key = f"settings_{ownership.value}_income_roll_up_period"

    label_col, control_col = st.columns(2, vertical_alignment="center")
    label_col.markdown("**Income roll-up month**", help=_INCOME_HELP)
    selected = control_col.selectbox(
        "Income roll-up month",
        options=list(entities.IncomeRollUpPeriod),
        index=list(entities.IncomeRollUpPeriod).index(settings.income_roll_up_period),
        format_func=_period_label,
        label_visibility="collapsed",
        key=key,
    )
    period = entities.IncomeRollUpPeriod(selected)

    if period is not settings.income_roll_up_period and _save(
        use_case,
        period,
        ownership,
    ):
        st.rerun()
