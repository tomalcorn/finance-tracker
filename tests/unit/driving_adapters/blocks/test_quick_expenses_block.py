"""Unit tests for the quick expenses block."""

import dataclasses
import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest
import streamlit.testing.v1 as st_test

from domain import entities
from driving_adapters.blocks import quick_expenses_block

if TYPE_CHECKING:
    from tests import conftest

USER_ID = "auth0|test-user-1"
BANK_ACCOUNT_ID = uuid.uuid4()

type QuickButtonRepo = conftest.FakeRepository[entities.QuickButtonModel]
type PaymentRepo = conftest.FakeRepository[entities.AnyPaymentModel]


@pytest.fixture(name="build_button")
def _build_button() -> Callable[..., entities.QuickButtonModel]:
    """Return a builder for a quick button, varying only what a test cares about."""

    def _build(
        name: str = "Coffee",
        expense: float | None = 3.5,
        icon: str | None = "☕",
        display_order: int = 0,
        mode: entities.QuickButtonMode = entities.QuickButtonMode.LOG,
    ) -> entities.QuickButtonModel:
        return entities.QuickButtonModel(
            user_id=USER_ID,
            name=name,
            mode=mode,
            expense=expense,
            # A prompt button is allowed to preset no account; a log one is not.
            bank_account_id=(
                None
                if mode is entities.QuickButtonMode.PROMPT and expense is None
                else BANK_ACCOUNT_ID
            ),
            icon=icon,
            display_order=display_order,
        )

    return _build


def test_tile_label_shows_the_icon_name_and_amount(
    build_button: Callable[..., entities.QuickButtonModel],
) -> None:
    # Arrange
    button = build_button()

    # Act
    label = quick_expenses_block._tile_label(button)

    # Assert
    assert label == "☕ Coffee — £3.50"


def test_tile_label_marks_a_button_that_asks_first(
    build_button: Callable[..., entities.QuickButtonModel],
) -> None:
    # Arrange - an ellipsis is the sign that tapping opens a form
    button = build_button(
        name="Groceries",
        expense=None,
        icon=None,
        mode=entities.QuickButtonMode.PROMPT,
    )

    # Act
    label = quick_expenses_block._tile_label(button)

    # Assert
    assert label == "Groceries …"


def test_tile_label_shows_a_prompt_buttons_preset_amount(
    build_button: Callable[..., entities.QuickButtonModel],
) -> None:
    # Arrange - a prompt button may still preset an amount to be corrected
    button = build_button(mode=entities.QuickButtonMode.PROMPT)

    # Act
    label = quick_expenses_block._tile_label(button)

    # Assert
    assert label == "☕ Coffee — £3.50 …"


def test_tile_label_omits_a_missing_icon(
    build_button: Callable[..., entities.QuickButtonModel],
) -> None:
    # Arrange
    button = build_button(icon=None)

    # Act
    label = quick_expenses_block._tile_label(button)

    # Assert
    assert label == "Coffee — £3.50"


def test_ordered_sorts_by_display_order_then_name(
    build_button: Callable[..., entities.QuickButtonModel],
) -> None:
    # Arrange - two buttons share a position, so the tie falls to the name
    first = build_button(name="Bus", display_order=1)
    second = build_button(name="Apple", display_order=1)
    third = build_button(name="Zebra", display_order=0)

    # Act
    ordered = quick_expenses_block._ordered([first, second, third])

    # Assert
    assert [button.name for button in ordered] == ["Zebra", "Apple", "Bus"]


@pytest.mark.parametrize(
    ("orders", "expected"),
    [
        ([], 0),
        ([0], 1),
        ([0, 4, 2], 5),
    ],
)
def test_next_display_order_follows_the_highest_existing(
    build_button: Callable[..., entities.QuickButtonModel],
    orders: list[int],
    expected: int,
) -> None:
    # Arrange
    buttons = [build_button(display_order=order) for order in orders]

    # Act
    next_order = quick_expenses_block._next_display_order(buttons)

    # Assert
    assert next_order == expected


@pytest.fixture(name="inputs")
def _inputs() -> quick_expenses_block._ButtonInputs:
    """Return the values a completed configuration dialog holds."""
    return quick_expenses_block._ButtonInputs(
        name="Lunch",
        mode=entities.QuickButtonMode.LOG,
        payment_name=None,
        expense=8.0,
        bank_account_id=str(BANK_ACCOUNT_ID),
        expense_source_id=None,
        icon="🍕",
        display_order=2,
    )


def test_button_row_carries_the_values_the_dialog_collected(
    inputs: quick_expenses_block._ButtonInputs,
) -> None:
    # Arrange - a new button, so no id to preserve.

    # Act
    row = quick_expenses_block._button_row(inputs, None)

    # Assert
    assert row == {
        "name": "Lunch",
        "mode": "log",
        "payment_name": None,
        "expense": 8.0,
        "bank_account_id": str(BANK_ACCOUNT_ID),
        "expense_source_id": None,
        "icon": "🍕",
        "display_order": 2,
    }


def test_button_row_carries_the_id_when_editing(
    inputs: quick_expenses_block._ButtonInputs,
    build_button: Callable[..., entities.QuickButtonModel],
) -> None:
    # Arrange - editing must upsert over the stored row, not add a second one
    existing = build_button()

    # Act
    row = quick_expenses_block._button_row(inputs, existing)

    # Assert
    assert row["id"] == str(existing.id)


def test_button_row_normalises_a_blank_icon_to_none(
    inputs: quick_expenses_block._ButtonInputs,
) -> None:
    # Arrange - an untouched icon field submits an empty string
    blank = dataclasses.replace(inputs, icon="")

    # Act
    row = quick_expenses_block._button_row(blank, None)

    # Assert
    assert row["icon"] is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("b", 1),
        ("missing", None),
        (None, None),
    ],
)
def test_option_index_locates_the_stored_value(
    value: str | None,
    expected: int | None,
) -> None:
    # Arrange
    options = ["a", "b", "c"]

    # Act
    index = quick_expenses_block._option_index(options, value)

    # Assert
    assert index == expected


def test_ownership_selector_offers_no_choice_without_a_joint_account() -> None:
    # Arrange - a user in no joint account has only personal finances.

    # Act
    ownership = quick_expenses_block.ownership_selector(has_joint_account=False)

    # Assert
    assert ownership is entities.OwnershipType.PERSONAL


def _render_wrapper(
    quick_button_repo: "QuickButtonRepo",
    payment_repo: "PaymentRepo",
    bank_account_map: dict[str, str],
) -> None:
    """Render the block for AppTest.

    Everything it needs is injected via AppTest ``kwargs`` — including the
    account map — because from_function re-runs this body in a fresh namespace
    where module-level names aren't visible.
    """
    from driving_adapters.blocks import quick_expenses_block as block
    from use_cases import log_quick_payment

    block.render(
        quick_button_repo,
        log_quick_payment.LogQuickPaymentUseCase(quick_button_repo, payment_repo),
        bank_account_map,
        {},
    )


@pytest.fixture(name="payment_repo")
def _payment_repo(build_payment_repo: Callable[..., "PaymentRepo"]) -> "PaymentRepo":
    """Return the payments repository a tap writes through."""
    return build_payment_repo(USER_ID)


@pytest.fixture(name="build_app_tester")
def _build_app_tester(
    payment_repo: "PaymentRepo",
    build_repo: "conftest.RepoBuilder",
) -> Callable[..., st_test.AppTest]:
    """Return a builder for an AppTest rendering the block over given buttons."""

    def _build(
        buttons: list[entities.QuickButtonModel] | None = None,
    ) -> st_test.AppTest:
        return st_test.AppTest.from_function(
            _render_wrapper,
            default_timeout=120,
            kwargs={
                "quick_button_repo": build_repo(
                    buttons or [],
                    parse=entities.QuickButtonModel.model_validate,
                    context={"user_id": USER_ID},
                ),
                "payment_repo": payment_repo,
                "bank_account_map": {str(BANK_ACCOUNT_ID): "Current"},
            },
        )

    return _build


def test_render_prompts_for_a_first_button_when_there_are_none(
    build_app_tester: Callable[..., st_test.AppTest],
) -> None:
    # Arrange
    app_tester = build_app_tester()

    # Act
    app_tester.run()

    # Assert
    assert "No quick buttons yet" in app_tester.info[0].value


def test_render_shows_a_tile_per_button(
    build_app_tester: Callable[..., st_test.AppTest],
    build_button: Callable[..., entities.QuickButtonModel],
) -> None:
    # Arrange
    buttons = [build_button(), build_button(name="Bus", display_order=1)]
    app_tester = build_app_tester(buttons)

    # Act
    app_tester.run()

    # Assert - one tile each, and no other button outside edit mode
    assert [button.label for button in app_tester.button] == [
        quick_expenses_block._tile_label(button) for button in buttons
    ]


def test_tapping_a_tile_logs_its_payment(
    build_app_tester: Callable[..., st_test.AppTest],
    build_button: Callable[..., entities.QuickButtonModel],
    payment_repo: "PaymentRepo",
) -> None:
    # Arrange
    button = build_button()
    app_tester = build_app_tester([button]).run()

    # Act
    app_tester.button(key=f"quick_button_{button.id}").click().run()

    # Assert
    assert [payment.name for payment in payment_repo.saved] == ["Coffee"]


def test_tapping_a_tile_while_editing_logs_nothing(
    build_app_tester: Callable[..., st_test.AppTest],
    build_button: Callable[..., entities.QuickButtonModel],
    payment_repo: "PaymentRepo",
) -> None:
    # Arrange - edit mode turns a tap into "configure this button"
    button = build_button()
    app_tester = build_app_tester([button]).run()
    app_tester.toggle[0].set_value(True).run()

    # Act
    app_tester.button(key=f"quick_button_{button.id}").click().run()

    # Assert
    assert payment_repo.saved == []


_LOG = entities.QuickButtonMode.LOG
_PROMPT = entities.QuickButtonMode.PROMPT


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"mode": _LOG}, True),
        ({"mode": _LOG, "name": ""}, False),
        ({"mode": _LOG, "expense": None}, False),
        ({"mode": _LOG, "bank_account_id": None}, False),
        ({"mode": _PROMPT, "expense": None, "bank_account_id": None}, True),
        ({"mode": _PROMPT, "name": ""}, False),
        ({"mode": _PROMPT}, True),
    ],
)
def test_can_save_requires_a_whole_payment_only_from_a_log_button(
    inputs: quick_expenses_block._ButtonInputs,
    overrides: dict[str, object],
    *,
    expected: bool,
) -> None:
    # Arrange - a prompt button presets nothing it cannot ask for later, but
    # every button needs the label its tile shows
    collected = dataclasses.replace(inputs, **overrides)

    # Act
    can_save = quick_expenses_block._can_save(collected)

    # Assert
    assert can_save is expected


def test_tapping_a_prompt_tile_logs_nothing_until_the_form_is_submitted(
    build_app_tester: Callable[..., st_test.AppTest],
    build_button: Callable[..., entities.QuickButtonModel],
    payment_repo: "PaymentRepo",
) -> None:
    # Arrange - the tap opens the form rather than writing straight away
    button = build_button(
        name="Groceries",
        expense=None,
        mode=entities.QuickButtonMode.PROMPT,
    )
    app_tester = build_app_tester([button]).run()

    # Act
    app_tester.button(key=f"quick_button_{button.id}").click().run()

    # Assert
    assert payment_repo.saved == []
