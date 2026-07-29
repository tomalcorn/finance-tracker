"""Writing a cross-linked expense/income pair across the ownership boundary.

A contribution to a joint account is two rows, one on each side: a personal
expense and a matching joint income, each pointing at the other through
``linked_payment_id``. Both the one-off Contribute action and the recurring
contribution a subscription books need exactly that pair written the same way,
so the ordering the foreign key forces lives here rather than in either use
case.

Free functions rather than a collaborator class: there is no state to hold, and
each caller already has the two repositories to hand. Errors are left alone —
every function raises the port's ``RepositoryError`` and each use case
translates it into its own failure type at its own boundary.
"""

from typing import TYPE_CHECKING

from domain import entities

if TYPE_CHECKING:
    import uuid

    from ports import repository

    type PaymentRepository = repository.Repository[entities.AnyPaymentModel]


def write_linked_pair(
    personal_repo: "PaymentRepository",
    joint_repo: "PaymentRepository",
    expense: entities.ExpensePaymentModel,
    income: entities.IncomePaymentModel,
) -> None:
    """Write both legs of a contribution and cross-link them.

    ``linked_payment_id`` is a foreign key onto ``payments``, so the pair cannot
    be cross-linked in two inserts: the expense is written unlinked, the income
    is written pointing back at it, and only then is the expense updated to point
    forward. ``income`` must already carry ``linked_payment_id=expense.id``.

    Args:
        personal_repo: Payments repository in personal mode.
        joint_repo: Payments repository in joint mode.
        expense: The personal leg, not yet written.
        income: The joint leg, pointing back at ``expense``.

    Raises:
        RepositoryError: If any of the three writes fails.

    """
    personal_repo.save_entities([expense])
    complete_linked_pair(personal_repo, joint_repo, expense, income)


def complete_linked_pair(
    personal_repo: "PaymentRepository",
    joint_repo: "PaymentRepository",
    expense: entities.ExpensePaymentModel,
    income: entities.IncomePaymentModel,
) -> None:
    """Write the income leg of an already-written expense, then link it forward.

    The second and third writes of :func:`write_linked_pair` on their own, for a
    pair whose expense landed but whose income did not.

    Raises:
        RepositoryError: If either write fails.

    """
    joint_repo.save_entities([income])
    link_expense_forward(personal_repo, expense, income.id)


def link_expense_forward(
    personal_repo: "PaymentRepository",
    expense: entities.ExpensePaymentModel,
    income_id: "uuid.UUID",
) -> None:
    """Point a written expense at the income leg that settles it.

    Entities are frozen, so the forward link is a new copy of the expense,
    upserted over the row already written. A no-op when the link is already in
    place, so a repair pass can call it unconditionally.

    Raises:
        RepositoryError: If the write fails.

    """
    if expense.linked_payment_id == income_id:
        return
    linked = entities.ExpensePaymentModel.model_validate(
        expense.model_copy(update={"linked_payment_id": income_id}),
    )
    personal_repo.save_entities([linked])
