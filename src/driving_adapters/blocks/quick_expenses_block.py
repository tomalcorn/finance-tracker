"""Quick expenses block: a grid of tappable buttons that each log one expense.

Three modes, driven by the "Edit buttons" toggle and the remove control beside
it. A tap means something different in each:

* **normal** — log the payment the button stands for.
* **edit** — open the button's configuration, pre-filled.
* **edit + remove armed** — remove the button, after a confirmation.

Only the remove arming is stored in session state; the edit toggle and the
dialogs are ordinary widgets keyed by the button they belong to.
"""

import dataclasses
import logging
from typing import TYPE_CHECKING

import streamlit as st

from domain import entities
from driving_adapters import lookups, ss_keys
from ports import errors as port_errors
from use_cases import errors as use_case_errors

if TYPE_CHECKING:
    from ports import repository
    from use_cases import log_quick_payment

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
    """The values the configuration dialog collected."""

    name: str
    expense: float
    bank_account_id: str
    expense_source_id: str | None
    icon: str | None
    display_order: int


def _tile_label(button: entities.QuickButtonModel) -> str:
    """Return the label shown on a button's tile, e.g. ``☕ Coffee — £3.50``."""
    name = f"{button.icon} {button.name}" if button.icon else button.name
    return f"{name} — £{button.expense:,.2f}"


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
) -> None:
    """Log the button's payment and confirm it, or explain why it did not log."""
    try:
        log_use_case.execute(button.id)
    except use_case_errors.QuickButtonNotFoundError:
        logger.exception("Quick button %s no longer exists.", button.id)
        st.error("That button no longer exists. Refresh the page to see the rest.")
        return
    except use_case_errors.QuickPaymentError:
        logger.exception("Failed to log quick payment for button %s.", button.id)
        st.error("Could not log that payment. Please try again or contact support.")
        return
    st.toast(f"{_tile_label(button)} logged", icon=":material/check_circle:")


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
        "Amount",
        min_value=0.0,
        value=existing.expense if existing else None,
        format="%.2f",
        key=f"{key}_expense",
    )
    bank_account_id = st.selectbox(
        "Bank account",
        options=bank_account_ids,
        index=_option_index(bank_account_ids, existing.bank_account_id)
        if existing
        else None,
        format_func=lookups.make_name_formatter(context.bank_account_map),
        key=f"{key}_bank_account",
    )
    expense_source_id = st.selectbox(
        "Expense source",
        options=expense_source_ids,
        index=_option_index(expense_source_ids, existing.expense_source_id)
        if existing
        else None,
        format_func=lookups.make_name_formatter(context.expense_source_map),
        help="Optional. Leave empty to log the payment uncategorised.",
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

    can_submit = bool(name) and expense is not None and expense > 0 and bank_account_id
    if st.button("Save", disabled=not can_submit, key=f"{key}_submit"):
        # The re-checks narrow the widget outputs for the type checker; the
        # button is unclickable unless can_submit held.
        if not (name and expense and bank_account_id):
            return
        row = _button_row(
            _ButtonInputs(
                name=name,
                expense=float(expense),
                bank_account_id=bank_account_id,
                expense_source_id=expense_source_id,
                icon=icon,
                display_order=int(display_order),
            ),
            existing,
        )
        try:
            context.repo.save_entities(context.repo.build_entities([row]))
        except port_errors.RepositoryError:
            logger.exception("Failed to save quick button %r.", name)
            st.error("Could not save the button. Please check the values and retry.")
            return
        st.rerun()


def _option_index(options: list[str], value: object) -> int | None:
    """Return where ``value`` sits in ``options``, or None when it is absent."""
    if value is None:
        return None
    try:
        return options.index(str(value))
    except ValueError:
        return None


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
    if not edit_mode:
        _log_payment(log_use_case, button)
        return
    if _remove_armed():
        _remove_dialog(context, button)
        return
    _config_dialog(context, button)


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
