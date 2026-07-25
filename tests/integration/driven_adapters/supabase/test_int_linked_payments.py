"""Integration test for the self-referential ``payments.linked_payment_id`` FK.

A contribution cross-links its two legs, so each row is referenced by the other.
Before migration 0009 the constraint defaulted to ``ON DELETE NO ACTION``, which
made *either* leg undeletable. Only a live-schema test can catch that: the
constraint is enforced by Postgres, not by any Python the unit suite exercises.
"""

import uuid
from collections.abc import Generator

import pytest
import st_supabase_connection

from domain import entities
from driven_adapters.supabase import repository as supabase_repos
from driving_adapters import cache

_USER_ID = "auth0|test-user-1"


@pytest.fixture(name="payment_repo")
def _payment_repo(
    connection: st_supabase_connection.SupabaseConnection,
) -> supabase_repos.SupabaseRepository:
    """Return a personal payments repository wired to the test connection."""
    return supabase_repos.payment_repository(
        _USER_ID,
        cache.StreamlitCache(),
        connection,
        entities.OwnershipType.PERSONAL,
    )


@pytest.fixture(name="linked_pair")
def _linked_pair(
    connection: st_supabase_connection.SupabaseConnection,
    payment_repo: supabase_repos.SupabaseRepository,
    yield_sample_bank_account: entities.BankAccountModel,
) -> Generator[tuple[entities.ExpensePaymentModel, entities.IncomePaymentModel]]:
    """Seed a cross-linked payment pair, as a contribution writes it.

    Written in the same order the contribution use case uses: the expense goes in
    unlinked, the income points back at it, and only then is the expense updated
    to point forward — the FK cannot be satisfied in two inserts.
    """
    expense = entities.ExpensePaymentModel(
        user_id=_USER_ID,
        name="Linked expense",
        expense=25.0,
        bank_account_id=yield_sample_bank_account.id,
    )
    payment_repo.save_entities([expense])

    income = entities.IncomePaymentModel(
        user_id=_USER_ID,
        name="Linked income",
        income=25.0,
        bank_account_id=yield_sample_bank_account.id,
        linked_payment_id=expense.id,
    )
    payment_repo.save_entities([income])

    linked_expense = entities.ExpensePaymentModel.model_validate(
        expense.model_copy(update={"linked_payment_id": income.id}),
    )
    payment_repo.save_entities([linked_expense])

    yield linked_expense, income

    # Clear the cross-links before deleting. The rows reference each other, so
    # under the pre-0009 schema neither could be deleted while both links were
    # set — a teardown that just deleted them would leave rows behind and break
    # the shared bank-account fixture for every later test.
    for payment_id in (linked_expense.id, income.id):
        connection.table("payments").update({"linked_payment_id": None}).eq(
            "id",
            str(payment_id),
        ).execute()
    for payment_id in (linked_expense.id, income.id):
        connection.table("payments").delete().eq("id", str(payment_id)).execute()


def test_deleting_one_leg_of_a_linked_pair_succeeds(
    payment_repo: supabase_repos.SupabaseRepository,
    linked_pair: tuple[entities.ExpensePaymentModel, entities.IncomePaymentModel],
) -> None:
    """Deleting a cross-linked payment is not blocked by the other leg's FK."""
    # Arrange
    expense, _ = linked_pair

    # Act
    payment_repo.apply_deletions([str(expense.id)])

    # Assert
    assert payment_repo.get_by_ids([expense.id]) == []


def test_deleting_one_leg_clears_the_survivors_back_reference(
    payment_repo: supabase_repos.SupabaseRepository,
    linked_pair: tuple[entities.ExpensePaymentModel, entities.IncomePaymentModel],
) -> None:
    """The surviving leg stays, with its now-dangling link set to NULL."""
    # Arrange
    expense, income = linked_pair

    # Act
    payment_repo.apply_deletions([str(expense.id)])

    # Assert
    survivor = payment_repo.get_by_ids([income.id])
    assert all(
        [
            len(survivor) == 1,
            survivor[0].linked_payment_id is None,
        ],
    )


def test_an_unlinked_payment_still_deletes(
    connection: st_supabase_connection.SupabaseConnection,
    payment_repo: supabase_repos.SupabaseRepository,
    yield_sample_bank_account: entities.BankAccountModel,
) -> None:
    """The constraint swap leaves ordinary deletes untouched."""
    # Arrange
    payment = entities.ExpensePaymentModel(
        user_id=_USER_ID,
        name="Unlinked",
        expense=5.0,
        bank_account_id=yield_sample_bank_account.id,
    )
    payment_repo.save_entities([payment])

    # Act
    payment_repo.apply_deletions([str(payment.id)])

    # Assert
    remaining = payment_repo.get_by_ids([payment.id])
    connection.table("payments").delete().eq("id", str(payment.id)).execute()
    assert remaining == []


def test_unknown_id_is_a_no_op(
    payment_repo: supabase_repos.SupabaseRepository,
) -> None:
    """Deleting an id that is not there does not raise."""
    # Arrange / Act
    payment_repo.apply_deletions([str(uuid.uuid4())])

    # Assert - reaching here without a RepositoryError is the assertion
    assert payment_repo.get_all() is not None
