"""Use case for recording a contribution from a personal account to a joint one."""

from typing import TYPE_CHECKING

from domain import entities
from ports import errors as port_errors
from use_cases import errors

if TYPE_CHECKING:
    import datetime
    import uuid

    from ports import repository


class ContributeToJointUseCase:
    """Records a contribution as a linked pair of payments.

    One call books the money leaving the contributor's personal ledger and
    arriving in the joint one:

    - a **personal expense** against the hidden "Joint" expense source, and
    - a matching **joint income** owned by the joint account.

    Each row's ``linked_payment_id`` points at the other, so the pair is
    traceable from either side. The joint row cannot be reached from the
    personal side by any other means: a personal repository is filtered to
    ``ownership_type='personal'`` and so can never see it.
    """

    def __init__(
        self,
        user_id: str,
        personal_payment_repo: "repository.Repository[entities.AnyPaymentModel]",
        joint_payment_repo: "repository.Repository[entities.AnyPaymentModel]",
        expense_source_repo: "repository.Repository[entities.ExpenseSourceModel]",
        joint_account_repo: "repository.Repository[entities.JointAccountModel]",
    ) -> None:
        """Construct ContributeToJointUseCase.

        Args:
            user_id: The contributing user.
            personal_payment_repo: Payments repository in personal mode.
            joint_payment_repo: Payments repository in joint mode.
            expense_source_repo: Personal expense sources, holding the hidden
                "Joint" source the personal leg is booked against.
            joint_account_repo: The joint accounts the user belongs to.

        """
        self._user_id = user_id
        self._personal_payment_repo = personal_payment_repo
        self._joint_payment_repo = joint_payment_repo
        self._expense_source_repo = expense_source_repo
        self._joint_account_repo = joint_account_repo

    def execute(
        self,
        amount: float,
        from_bank_account_id: "uuid.UUID",
        to_bank_account_id: "uuid.UUID",
        payment_date: "datetime.date",
    ) -> None:
        """Record a contribution to the user's joint account.

        Args:
            amount: The amount contributed. Must be greater than zero.
            from_bank_account_id: The personal bank account the money leaves.
            to_bank_account_id: The joint bank account the money arrives in.
            payment_date: The date of both legs.

        Raises:
            ContributionAmountError: If ``amount`` is not greater than zero.
            NoJointAccountToContributeToError: If the user belongs to no joint
                account, so there is nothing to contribute to.
            JointExpenseSourceNotFoundError: If the hidden "Joint" expense
                source is missing, so the personal leg has nothing to book
                against.
            ContributionWriteError: If any of the three writes fails.

        """
        if amount <= 0:
            raise errors.ContributionAmountError(amount)

        account = self._resolve_joint_account()
        expense_source_id = self._resolve_joint_expense_source()
        name = f"Joint: {account.name}"

        expense = entities.ExpensePaymentModel(
            user_id=self._user_id,
            name=name,
            expense=amount,
            payment_date=payment_date,
            bank_account_id=from_bank_account_id,
            expense_source_id=expense_source_id,
        )
        income = entities.IncomePaymentModel(
            user_id=self._user_id,
            name=name,
            income=amount,
            payment_date=payment_date,
            bank_account_id=to_bank_account_id,
            ownership_type=entities.OwnershipType.JOINT,
            joint_account_id=account.id,
            linked_payment_id=expense.id,
        )

        self._write_pair(expense, income)

    def _resolve_joint_account(self) -> entities.JointAccountModel:
        """Return the user's joint account.

        Raises:
            NoJointAccountToContributeToError: If the user belongs to none.
            ContributionWriteError: If the account cannot be read.

        """
        try:
            accounts = self._joint_account_repo.get_all()
        except port_errors.RepositoryError as e:
            msg = f"Failed to read the joint account for user {self._user_id}: {e}"
            raise errors.ContributionWriteError(msg) from e

        if not accounts:
            raise errors.NoJointAccountToContributeToError(self._user_id)
        return accounts[0]

    def _resolve_joint_expense_source(self) -> "uuid.UUID":
        """Return the id of the hidden "Joint" expense source.

        Raises:
            JointExpenseSourceNotFoundError: If the source is missing.
            ContributionWriteError: If the sources cannot be read.

        """
        try:
            expense_sources = self._expense_source_repo.get_all()
        except port_errors.RepositoryError as e:
            msg = f"Failed to read expense sources for user {self._user_id}: {e}"
            raise errors.ContributionWriteError(msg) from e

        match = next(
            (
                expense_source
                for expense_source in expense_sources
                if expense_source.name == entities.BudgetTrackerName.JOINT
            ),
            None,
        )
        if match is None:
            raise errors.JointExpenseSourceNotFoundError(self._user_id)
        return match.id

    def _write_pair(
        self,
        expense: entities.ExpensePaymentModel,
        income: entities.IncomePaymentModel,
    ) -> None:
        """Write the expense/income pair and cross-link the two rows.

        ``linked_payment_id`` is a foreign key onto ``payments``, so the pair
        cannot be cross-linked in two inserts: the expense is written unlinked,
        the income is written pointing back at it, and only then is the expense
        updated to point forward.

        Raises:
            ContributionWriteError: If any of the three writes fails.

        """
        try:
            self._personal_payment_repo.save(expense)
            self._joint_payment_repo.save(income)

            expense.linked_payment_id = income.id
            self._personal_payment_repo.save(expense)
        except port_errors.RepositoryError as e:
            msg = (
                f"Failed to record a contribution of {expense.expense} to joint "
                f"account {income.joint_account_id} for user {self._user_id}: {e}"
            )
            raise errors.ContributionWriteError(msg) from e
