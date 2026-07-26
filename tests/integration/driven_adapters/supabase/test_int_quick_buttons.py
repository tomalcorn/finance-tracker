"""Integration tests for the quick-buttons repository against the test DB.

Covers the round trip the Quick Expenses page depends on: a button built
through the repository's gate reaches the live table, reads back with its
preset intact, and can be removed again. Together they check the 0010 schema
against ``QuickButtonModel`` — a column the migration and the entity disagree
about fails here rather than at a tap on the phone.
"""

import typing
import uuid

import pytest
import st_supabase_connection

from domain import entities, read_models
from driven_adapters.supabase import repository as supabase_repos
from driving_adapters import cache

_USER_ID = "auth0|test-user-1"

type QuickButtonRepo = supabase_repos.SupabaseRepository[
    entities.QuickButtonModel,
    read_models.QuickButtonView,
]


@pytest.fixture(name="quick_button_repo")
def _quick_button_repo(
    connection: st_supabase_connection.SupabaseConnection,
) -> QuickButtonRepo:
    """Return a quick-buttons repository wired to the test connection."""
    return supabase_repos.quick_button_repository(
        _USER_ID,
        cache.StreamlitCache(),
        connection,
        entities.OwnershipType.PERSONAL,
    )


@pytest.fixture(name="stored_button")
def _stored_button(
    quick_button_repo: QuickButtonRepo,
    connection: st_supabase_connection.SupabaseConnection,
    yield_sample_bank_account: entities.BankAccountModel,
) -> typing.Generator[entities.QuickButtonModel, None, None]:
    """Write one button through the gate and remove it afterwards."""
    cache._get_data_cached.clear()
    built = quick_button_repo.build_entities(
        [
            {
                "name": "Coffee",
                "expense": 3.5,
                "bank_account_id": str(yield_sample_bank_account.id),
                "icon": "☕",
                "display_order": 1,
            },
        ],
    )
    quick_button_repo.save_entities(built)
    cache._get_data_cached.clear()

    yield built[0]

    connection.table("quick_buttons").delete().eq("id", str(built[0].id)).execute()
    cache._get_data_cached.clear()


def _get_by_id(
    repo: QuickButtonRepo,
    button_id: uuid.UUID,
) -> entities.QuickButtonModel | None:
    """Read a single button by ID through the repository."""
    matches = repo.get_by_ids([button_id])
    return matches[0] if matches else None


def test_a_saved_button_reads_back_with_its_preset(
    quick_button_repo: QuickButtonRepo,
    stored_button: entities.QuickButtonModel,
    yield_sample_bank_account: entities.BankAccountModel,
) -> None:
    """Every field the gate wrote survives the round trip to the table."""
    # Act
    stored = _get_by_id(quick_button_repo, stored_button.id)

    # Assert
    preset_survived = stored is not None and all(
        [
            stored.name == "Coffee",
            stored.expense == stored_button.expense,
            stored.bank_account_id == yield_sample_bank_account.id,
            stored.icon == "☕",
            stored.display_order == 1,
            stored.ownership_type is entities.OwnershipType.PERSONAL,
        ],
    )
    assert preset_survived


def test_a_prompt_button_stores_without_the_fields_it_defers(
    quick_button_repo: QuickButtonRepo,
    connection: st_supabase_connection.SupabaseConnection,
) -> None:
    """The columns 0012 made nullable really do accept a row without them."""
    # Arrange
    cache._get_data_cached.clear()
    built = quick_button_repo.build_entities(
        [
            {
                "name": "Groceries",
                "mode": entities.QuickButtonMode.PROMPT.value,
            },
        ],
    )

    # Act
    quick_button_repo.save_entities(built)
    cache._get_data_cached.clear()
    stored = _get_by_id(quick_button_repo, built[0].id)

    # Clean up
    connection.table("quick_buttons").delete().eq("id", str(built[0].id)).execute()
    cache._get_data_cached.clear()

    # Assert
    deferred_fields_are_empty = stored is not None and all(
        [
            stored.mode is entities.QuickButtonMode.PROMPT,
            stored.expense is None,
            stored.bank_account_id is None,
        ],
    )
    assert deferred_fields_are_empty


def test_apply_deletions_removes_a_button(
    quick_button_repo: QuickButtonRepo,
    stored_button: entities.QuickButtonModel,
) -> None:
    """A removed button is gone on the next read."""
    # Act
    quick_button_repo.apply_deletions([str(stored_button.id)])
    cache._get_data_cached.clear()

    # Assert
    assert _get_by_id(quick_button_repo, stored_button.id) is None
