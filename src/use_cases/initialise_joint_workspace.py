"""Joint workspace initialisation.

Seeds default budget trackers and hidden expense sources for a joint account,
stamping joint ownership on every row it creates. The personal-side "Joint"
budget tracker and its hidden expense source are deliberately absent: they are
the personal-side anchor for contributions, meaningless inside the joint account
itself (see #191).
"""

from typing import TYPE_CHECKING

from domain import entities
from ports import errors as port_errors
from use_cases import errors

if TYPE_CHECKING:
    import uuid

    from ports import repository

# The joint account seeds every budget tracker the personal workspace does
# except JOINT: a joint-owned copy of the personal contribution anchor would be
# meaningless and would double up the contribution model.
_JOINT_BUDGET_TRACKER_NAMES = tuple(
    name
    for name in entities.BudgetTrackerName
    if name is not entities.BudgetTrackerName.JOINT
)

# Hidden expense sources are needed for these joint budget tracker names — the
# personal hidden set (JOINT, ONE_OFFS, SAVINGS) minus JOINT.
_HIDDEN_EXPENSE_SOURCE_BT_NAMES = (
    entities.BudgetTrackerName.ONE_OFFS,
    entities.BudgetTrackerName.SAVINGS,
)


class InitialiseJointWorkspaceUseCase:
    """Seeds default budget trackers and hidden expense sources for a joint account."""

    def __init__(
        self,
        user_id: str,
        budget_tracker_repo: "repository.Repository[entities.BudgetTrackerItemModel]",
        expense_source_repo: "repository.Repository[entities.ExpenseSourceModel]",
        joint_account_repo: "repository.Repository[entities.JointAccountModel]",
    ) -> None:
        """Construct InitialiseJointWorkspaceUseCase.

        Args:
            user_id: The member triggering the seed; stamped as ``user_id`` on
                every created row.
            budget_tracker_repo: Budget trackers repository in joint mode.
            expense_source_repo: Expense sources repository in joint mode.
            joint_account_repo: The joint accounts the user belongs to, used to
                resolve the account id stamped on every created row.

        """
        self._user_id = user_id
        self._bt_repo = budget_tracker_repo
        self._es_repo = expense_source_repo
        self._joint_account_repo = joint_account_repo

    def execute(self) -> None:
        """Ensure the user's joint account has its default trackers and sources.

        Idempotent (create-if-missing), matching the personal workspace use case.

        Raises:
            NoJointAccountToInitialiseError: If the user belongs to no joint
                account, so there is nothing to seed.
            JointDataAccessError: If any repository operation fails.

        """
        try:
            account = self._resolve_joint_account()
            self._ensure_default_budget_trackers(account.id)

            # Fetch all budget tracker rows again to get IDs
            all_bts = self._bt_repo.get_all()
            bt_id_by_name = {bt.name: bt.id for bt in all_bts}

            self._ensure_hidden_expense_sources(account.id, bt_id_by_name)

        except port_errors.RepositoryError as e:
            # Wrap a persistence failure; a genuine bug propagates untouched.
            msg = f"Failed to initialise joint workspace for user {self._user_id}: {e}"
            raise errors.JointDataAccessError(msg) from e

    def _resolve_joint_account(self) -> entities.JointAccountModel:
        """Return the user's one joint account.

        Raises:
            NoJointAccountToInitialiseError: If the user belongs to none.

        """
        accounts = self._joint_account_repo.get_all()
        if not accounts:
            raise errors.NoJointAccountToInitialiseError(self._user_id)
        return accounts[0]

    def _ensure_default_budget_trackers(self, joint_account_id: "uuid.UUID") -> None:
        """Create any missing joint budget tracker rows for the account."""
        existing_bts = self._bt_repo.get_all()
        existing_names = {bt.name for bt in existing_bts}

        for name in _JOINT_BUDGET_TRACKER_NAMES:
            if name not in existing_names:
                bt = entities.BudgetTrackerItemModel(
                    user_id=self._user_id,
                    name=name,
                    ownership_type=entities.OwnershipType.JOINT,
                    joint_account_id=joint_account_id,
                )
                self._bt_repo.save(bt)

    def _ensure_hidden_expense_sources(
        self,
        joint_account_id: "uuid.UUID",
        bt_id_by_name: dict[entities.BudgetTrackerName, "uuid.UUID"],
    ) -> None:
        """For each hidden budget tracker name, ensure an expense source links to it."""
        existing_es = self._es_repo.get_all()
        es_by_name = {es.name: es for es in existing_es}

        for bt_name in _HIDDEN_EXPENSE_SOURCE_BT_NAMES:
            bt_id = bt_id_by_name[bt_name]

            expense_source_name = bt_name.value
            existing = es_by_name.get(expense_source_name)

            if existing is None:
                new_es = entities.ExpenseSourceModel(
                    user_id=self._user_id,
                    name=expense_source_name,
                    budget_tracker_ids=[bt_id],
                    ownership_type=entities.OwnershipType.JOINT,
                    joint_account_id=joint_account_id,
                )
                self._es_repo.save(new_es)
            # Ensure the budget_tracker_ids list contains bt_id
            elif existing.budget_tracker_ids is None:
                existing.budget_tracker_ids = [bt_id]
                self._es_repo.save(existing)
            elif bt_id not in existing.budget_tracker_ids:
                existing.budget_tracker_ids.append(bt_id)
                self._es_repo.save(existing)
