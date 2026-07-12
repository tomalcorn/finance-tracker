"""Workspace initialisation.

Seeds default budget trackers and hidden expense sources for a user.
"""

from typing import TYPE_CHECKING

from domain import entities
from ports import errors as port_errors
from use_cases import errors

if TYPE_CHECKING:
    import uuid

    from ports import repository

# Hidden expense sources are needed for these budget tracker names
_HIDDEN_EXPENSE_SOURCE_BT_NAMES = (
    entities.BudgetTrackerName.JOINT,
    entities.BudgetTrackerName.ONE_OFFS,
    entities.BudgetTrackerName.SAVINGS,
)


class InitialiseUserWorkspaceUseCase:
    """Seeds default budget trackers and hidden expense sources for a user."""

    def __init__(
        self,
        user_id: str,
        budget_tracker_repo: "repository.Repository[entities.BudgetTrackerItemModel]",
        expense_source_repo: "repository.Repository[entities.ExpenseSourceModel]",
    ) -> None:
        """Construct InitialiseUserWorkspaceUseCase."""
        self._user_id = user_id
        self._bt_repo = budget_tracker_repo
        self._es_repo = expense_source_repo

    def execute(self) -> None:
        """Ensure the user has default budget tracker rows and linked expense sources.

        Raises:
            WorkspaceInitializationError: If any repository operation fails.

        """
        try:
            self._ensure_default_budget_trackers()

            # Fetch all budget tracker rows again to get IDs
            all_bts = self._bt_repo.get_all()
            bt_id_by_name = {bt.name: bt.id for bt in all_bts}

            self._ensure_hidden_expense_sources(bt_id_by_name)

        except port_errors.RepositoryError as e:
            # Wrap a persistence failure; a genuine bug propagates untouched.
            msg = f"Failed to initialise workspace for user {self._user_id}: {e}"
            raise errors.DataAccessError(msg) from e

    def _ensure_default_budget_trackers(self) -> None:
        """Create any missing budget tracker rows for the user."""
        existing_bts = self._bt_repo.get_all()
        existing_names = {bt.name for bt in existing_bts}

        for name in entities.BudgetTrackerName:
            if name not in existing_names:
                bt = entities.BudgetTrackerItemModel(
                    user_id=self._user_id,
                    name=name,
                )
                self._bt_repo.save(bt)

    def _ensure_hidden_expense_sources(
        self,
        bt_id_by_name: dict[entities.BudgetTrackerName, "uuid.UUID"],
    ) -> None:
        """For each hidden budget tracker name, ensure an expense source links to it."""
        # Fetch existing expense sources for this user
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
                )
                self._es_repo.save(new_es)
            # Ensure the budget_tracker_ids list contains bt_id
            elif existing.budget_tracker_ids is None:
                existing.budget_tracker_ids = [bt_id]
                self._es_repo.save(existing)
            elif bt_id not in existing.budget_tracker_ids:
                existing.budget_tracker_ids.append(bt_id)
                self._es_repo.save(existing)
