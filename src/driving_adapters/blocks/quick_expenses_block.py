"""Quick expenses block: a grid of tappable buttons that each log one expense.

A tap does one of two things, decided per button by its mode: a ``LOG`` button
writes its preset straight away, a ``PROMPT`` button opens a payment form
pre-filled with whatever it holds so the varying part can be typed in first.

On top of that sit three editing modes, driven by the "Edit buttons" toggle and
the remove control beside it. A tap means something different in each:

* **normal** — log the payment, or open the form that completes it.
* **edit** — open the button's configuration, pre-filled.
* **edit + remove armed** — remove the button, after a confirmation.

Session state holds only the remove arming and the pending confirmation toast;
the edit toggle and the dialogs are ordinary widgets keyed by the button they
belong to.
"""

import dataclasses
import datetime
import logging
import uuid
from typing import TYPE_CHECKING

import streamlit as st

from domain import entities
from driving_adapters import lookups, ss_keys
from ports import errors as port_errors
from use_cases import errors as use_case_errors
from use_cases import log_quick_payment

if TYPE_CHECKING:
    from ports import repository

logger = logging.getLogger(__name__)

_COLUMNS = 2
_TILE_CONTAINER_KEY = "quick_button_tiles"

# Tap targets, not desktop buttons: the tiles are stretched to the column width
# by `width="stretch"` and given a thumb-sized height here. Scoped to the tile
# container's generated `st-key-` class so no other button on the page is
# affected.
_TILE_CSS = f"""
<style>
.st-key-{_TILE_CONTAINER_KEY} button {{
    min-height: 4.5rem;
    font-size: 1.05rem;
}}
</style>
"""


@dataclasses.dataclass(frozen=True)
class _EditContext:
    """What the add, edit, and remove flows need to read and write a button.

    Bundled rather than threaded through each call: the three flows all want the
    same four things, and a tap has to hand them on to whichever it opens.
    """

    repo: "repository.Repository[entities.QuickButtonModel]"
    bank_account_map: dict[str, str]
    expense_source_map: dict[str, str]
    buttons: "list[entities.QuickButtonModel]"


@dataclasses.dataclass(frozen=True)
class _ButtonInputs:
    """The values the configuration dialog collected.

    Everything but the name and the mode is optional, because a ``PROMPT``
    button is allowed to leave the payment fields blank until it is tapped.
    """

    name: str
    mode: entities.QuickButtonMode
    expense: float | None
    bank_account_id: str | None
    expense_source_id: str | None
    icon: str | None
    display_order: int


def _tile_label(button: entities.QuickButtonModel) -> str:
    """Return the label shown on a button's tile.

    A preset amount is shown (``☕ Coffee — £3.50``); a button that asks before
    it logs ends in an ellipsis, the usual sign that tapping opens something
    rather than acting immediately.
    """
    label = f"{button.icon} {button.name}" if button.icon else button.name
    if button.expense is not None:
        label = f"{label} — £{button.expense:,.2f}"
    if button.mode is entities.QuickButtonMode.PROMPT:
        label = f"{label} …"
    return label


def _ordered(
    buttons: "list[entities.QuickButtonModel]",
) -> list[entities.QuickButtonModel]:
    """Return the buttons in display order, ties broken by name."""
    return sorted(buttons, key=lambda button: (button.display_order, button.name))


def _next_display_order(buttons: "list[entities.QuickButtonModel]") -> int:
    """Return the display order that puts a new button after the existing ones."""
    return max((button.display_order for button in buttons), default=-1) + 1


def _remove_armed() -> bool:
    """Return whether the next tap removes the button it lands on."""
    return bool(st.session_state.get(ss_keys.SSKeys.QUICK_BUTTONS_REMOVE_ARMED, False))


def _set_remove_armed(*, armed: bool) -> None:
    """Arm or disarm remove mode."""
    st.session_state[ss_keys.SSKeys.QUICK_BUTTONS_REMOVE_ARMED] = armed


def _queue_toast(message: str) -> None:
    """Hold a confirmation for the next run to show.

    A write is followed by a rerun, which would cut a toast raised here short, so
    the message waits in session state and :func:`_flush_toast` raises it once
    the page has been rebuilt.
    """
    st.session_state[ss_keys.SSKeys.QUICK_BUTTONS_TOAST] = message


def _flush_toast() -> None:
    """Show the confirmation left by the previous run, if there is one."""
    message = st.session_state.pop(ss_keys.SSKeys.QUICK_BUTTONS_TOAST, None)
    if message:
        st.toast(str(message), icon=":material/check_circle:")


def _can_log(inputs: _ButtonInputs) -> bool:
    """Return whether the collected values make a saveable button.

    A name is always needed. A ``LOG`` button additionally needs everything a
    payment cannot be written without, because a tap gives it no second chance
    to ask — the same rule the entity enforces, applied here so the dialog can
    disable Save rather than let the write fail.
    """
    if not inputs.name:
        return False
    if inputs.mode is entities.QuickButtonMode.PROMPT:
        return True
    return bool(inputs.expense) and bool(inputs.bank_account_id)


def _button_row(
    inputs: _ButtonInputs,
    existing: entities.QuickButtonModel | None,
) -> dict[str, object]:
    """Return the raw row a dialog submission writes.

    Editing carries the existing id, so the write upserts over that row rather
    than adding a second one; the ownership context is filled in by the
    repository's gate either way.
    """
    row: dict[str, object] = {
        "name": inputs.name,
        "mode": inputs.mode.value,
        "expense": inputs.expense,
        "bank_account_id": inputs.bank_account_id,
        "expense_source_id": inputs.expense_source_id,
        "icon": inputs.icon or None,
        "display_order": inputs.display_order,
    }
    if existing is not None:
        row["id"] = str(existing.id)
    return row


def _log_payment(
    log_use_case: "log_quick_payment.LogQuickPaymentUseCase",
    button: entities.QuickButtonModel,
    details: log_quick_payment.QuickPaymentDetails | None = None,
) -> bool:
    """Log a button's payment, reporting whether it was written.

    Args:
        log_use_case: The use case that writes the payment.
        button: The button that was tapped.
        details: What a prompt button's form collected, if any.

    Returns:
        Whether the payment was logged.

    """
    try:
        payment = log_use_case.execute(button.id, details)
    except use_case_errors.QuickButtonNotFoundError:
        logger.exception("Quick button %s no longer exists.", button.id)
        st.error("That button no longer exists. Refresh the page to see the rest.")
        return False
    except use_case_errors.IncompleteQuickPaymentError:
        logger.exception("Quick button %s was tapped incomplete.", button.id)
        st.error("That payment is missing an amount or a bank account.")
        return False
    except use_case_errors.QuickPaymentError:
        logger.exception("Failed to log quick payment for button %s.", button.id)
        st.error("Could not log that payment. Please try again or contact support.")
        return False
    _queue_toast(f"{payment.name} — £{payment.expense:,.2f} logged")
    return True


def _option_index(options: list[str], value: object) -> int | None:
    """Return where ``value`` sits in ``options``, or None when it is absent."""
    if value is None:
        return None
    try:
        return options.index(str(value))
    except ValueError:
        return None


@st.dialog("Log a payment")
def _prompt_dialog(
    context: _EditContext,
    log_use_case: "log_quick_payment.LogQuickPaymentUseCase",
    button: entities.QuickButtonModel,
) -> None:
    """Collect what a prompt button left blank, then log the payment.

    Pre-filled from the preset, so a button that fixes everything but the amount
    opens with only the amount waiting.
    """
    bank_account_ids = list(context.bank_account_map)
    expense_source_ids = list(context.expense_source_map)
    key = f"quick_prompt_{button.id}"

    name = st.text_input("Name", value=button.name, key=f"{key}_name")
    expense = st.number_input(
        "Amount",
        min_value=0.0,
        value=button.expense,
        format="%.2f",
        key=f"{key}_expense",
    )
    payment_date = st.date_input(
        "Date",
        value=datetime.datetime.now(tz=datetime.UTC).date(),
        key=f"{key}_date",
    )
    bank_account_id = st.selectbox(
        "Bank account",
        options=bank_account_ids,
        index=_option_index(bank_account_ids, button.bank_account_id),
        format_func=lookups.make_name_formatter(context.bank_account_map),
        key=f"{key}_bank_account",
    )
    expense_source_id = st.selectbox(
        "Expense source",
        options=expense_source_ids,
        index=_option_index(expense_source_ids, button.expense_source_id),
        format_func=lookups.make_name_formatter(context.expense_source_map),
        key=f"{key}_expense_source",
    )

    can_submit = bool(name) and bool(expense) and bool(bank_account_id)
    if st.button("Log payment", disabled=not can_submit, key=f"{key}_submit"):
        # The re-checks narrow the widget outputs for the type checker; the
        # button is unclickable unless can_submit held.
        if not (name and expense and bank_account_id):
            return
        details = log_quick_payment.QuickPaymentDetails(
            name=name,
            expense=float(expense),
            bank_account_id=uuid.UUID(bank_account_id),
            expense_source_id=(
                uuid.UUID(expense_source_id) if expense_source_id else None
            ),
            payment_date=(
                payment_date if isinstance(payment_date, datetime.date) else None
            ),
        )
        if _log_payment(log_use_case, button, details):
            st.rerun()


@st.dialog("Quick button")
def _config_dialog(
    context: _EditContext,
    existing: entities.QuickButtonModel | None,
) -> None:
    """Render the add/edit dialog, pre-filled when editing an existing button."""
    if not context.bank_account_map:
        st.warning(
            "You need a bank account before a quick button has somewhere to log "
            "from. Add one on your dashboard first, then come back.",
        )
        return

    bank_account_ids = list(context.bank_account_map)
    expense_source_ids = list(context.expense_source_map)
    key = f"quick_button_form_{existing.id if existing else 'new'}"

    asks_first = st.toggle(
        "Ask for details when tapped",
        value=existing is not None and existing.mode is entities.QuickButtonMode.PROMPT,
        help=(
            "On: a tap opens this form pre-filled, so anything left blank here "
            "can be filled in at the till. Off: a tap logs the payment straight "
            "away, so the amount and bank account are needed now."
        ),
        key=f"{key}_asks_first",
    )
    mode = (
        entities.QuickButtonMode.PROMPT if asks_first else entities.QuickButtonMode.LOG
    )
    optional = " (optional)" if asks_first else ""

    icon = st.text_input(
        "Icon",
        value=existing.icon if existing else "",
        max_chars=2,
        help="An optional emoji, shown before the name.",
        key=f"{key}_icon",
    )
    name = st.text_input(
        "Name",
        value=existing.name if existing else "",
        key=f"{key}_name",
    )
    expense = st.number_input(
        f"Amount{optional}",
        min_value=0.0,
        value=existing.expense if existing else None,
        format="%.2f",
        key=f"{key}_expense",
    )
    bank_account_id = st.selectbox(
        f"Bank account{optional}",
        options=bank_account_ids,
        index=_option_index(bank_account_ids, existing.bank_account_id)
        if existing
        else None,
        format_func=lookups.make_name_formatter(context.bank_account_map),
        key=f"{key}_bank_account",
    )
    expense_source_id = st.selectbox(
        "Expense source (optional)",
        options=expense_source_ids,
        index=_option_index(expense_source_ids, existing.expense_source_id)
        if existing
        else None,
        format_func=lookups.make_name_formatter(context.expense_source_map),
        help="Leave empty to log the payment uncategorised.",
        key=f"{key}_expense_source",
    )
    display_order = st.number_input(
        "Position",
        min_value=0,
        step=1,
        value=existing.display_order
        if existing
        else _next_display_order(context.buttons),
        help="Lower numbers appear first.",
        key=f"{key}_display_order",
    )

    inputs = _ButtonInputs(
        name=name,
        mode=mode,
        expense=float(expense) if expense else None,
        bank_account_id=bank_account_id,
        expense_source_id=expense_source_id,
        icon=icon,
        display_order=int(display_order),
    )
    if st.button("Save", disabled=not _can_log(inputs), key=f"{key}_submit"):
        row = _button_row(inputs, existing)
        try:
            context.repo.save_entities(context.repo.build_entities([row]))
        except port_errors.RepositoryError:
            logger.exception("Failed to save quick button %r.", name)
            st.error("Could not save the button. Please check the values and retry.")
            return
        st.rerun()


@st.dialog("Remove quick button")
def _remove_dialog(
    context: _EditContext,
    button: entities.QuickButtonModel,
) -> None:
    """Confirm removing a button, then delete it."""
    st.write(f"Remove **{_tile_label(button)}**?")
    st.caption("The payments it has already logged are not affected.")

    confirm, cancel = st.columns(2)
    if cancel.button("Cancel", width="stretch", key=f"quick_remove_cancel_{button.id}"):
        st.rerun()
    if confirm.button(
        "Remove",
        type="primary",
        width="stretch",
        key=f"quick_remove_confirm_{button.id}",
    ):
        try:
            context.repo.apply_deletions([str(button.id)])
        except port_errors.RepositoryError:
            logger.exception("Failed to remove quick button %s.", button.id)
            st.error("Could not remove the button. Please try again.")
            return
        _set_remove_armed(armed=False)
        st.rerun()


def ownership_selector(*, has_joint_account: bool) -> entities.OwnershipType:
    """Return the half of the finances taps are logged against.

    Rendered only for a user who belongs to a joint account; everyone else logs
    personally and is shown no control to choose otherwise.
    """
    if not has_joint_account:
        return entities.OwnershipType.PERSONAL
    labels = {
        "Personal": entities.OwnershipType.PERSONAL,
        "Joint": entities.OwnershipType.JOINT,
    }
    selected = st.segmented_control(
        "Log to",
        options=list(labels),
        default="Personal",
        key="quick_expenses_ownership",
    )
    return labels.get(str(selected), entities.OwnershipType.PERSONAL)


def _render_edit_controls(context: _EditContext) -> None:
    """Render the add and remove-mode controls shown while editing."""
    add_col, remove_col, _ = st.columns([0.15, 0.15, 0.7])
    if add_col.button("", icon=":material/add_2:", key="quick_button_add"):
        _config_dialog(context, None)
    armed = _remove_armed()
    if remove_col.button(
        "",
        icon=":material/remove:",
        type="primary" if armed else "secondary",
        key="quick_button_remove_mode",
    ):
        _set_remove_armed(armed=not armed)
        st.rerun()

    if _remove_armed():
        st.warning("Remove mode: tap a button to remove it.")
    else:
        st.caption("Tap a button to change it, or + to add one.")


def _handle_tap(
    context: _EditContext,
    log_use_case: "log_quick_payment.LogQuickPaymentUseCase",
    button: entities.QuickButtonModel,
    *,
    edit_mode: bool,
) -> None:
    """Do whatever tapping ``button`` means in the current mode."""
    if edit_mode:
        if _remove_armed():
            _remove_dialog(context, button)
            return
        _config_dialog(context, button)
        return
    if button.mode is entities.QuickButtonMode.PROMPT:
        _prompt_dialog(context, log_use_case, button)
        return
    if _log_payment(log_use_case, button):
        st.rerun()


def render(
    quick_button_repo: "repository.Repository[entities.QuickButtonModel]",
    log_use_case: "log_quick_payment.LogQuickPaymentUseCase",
    bank_account_map: dict[str, str],
    expense_source_map: dict[str, str],
) -> None:
    """Render the quick expenses block.

    Args:
        quick_button_repo: The buttons to show, and where edits are written.
        log_use_case: Logs the payment behind a tapped button.
        bank_account_map: ``{id: name}`` of the accounts a button can log from.
        expense_source_map: ``{id: name}`` of the sources a button can book to.

    """
    _flush_toast()
    buttons = _ordered(quick_button_repo.get_all())
    context = _EditContext(
        repo=quick_button_repo,
        bank_account_map=bank_account_map,
        expense_source_map=expense_source_map,
        buttons=buttons,
    )

    edit_mode = st.toggle("Edit buttons", key="quick_expenses_edit_mode")
    if not edit_mode and _remove_armed():
        _set_remove_armed(armed=False)

    if edit_mode:
        _render_edit_controls(context)

    if not buttons:
        st.info(
            "No quick buttons yet. Turn on **Edit buttons** and tap **+** to add "
            "your first one.",
        )
        return

    st.markdown(_TILE_CSS, unsafe_allow_html=True)
    with st.container(key=_TILE_CONTAINER_KEY):
        columns = st.columns(_COLUMNS)
        for index, button in enumerate(buttons):
            if columns[index % _COLUMNS].button(
                _tile_label(button),
                width="stretch",
                key=f"quick_button_{button.id}",
            ):
                _handle_tap(context, log_use_case, button, edit_mode=edit_mode)
