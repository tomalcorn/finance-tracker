"""Workspace initialisation.

Seeds default budget trackers and hidden expense sources for a user.
"""

import uuid
from typing import cast

from domain import entities
from ports import repository
from use_cases import errors

# Hidden expense sources are needed for these budget tracker names
_HIDDEN_EXPENSE_SOURCE_BT_NAMES = (
    entities.BudgetTrackerName.JOINT,
    entities.BudgetTrackerName.ONE_OFFS,
    entities.BudgetTrackerName.SAVINGS,
)


class InitializeUserWorkspaceUseCase:
    """Seeds default budget trackers and hidden expense sources for a user."""

    def __init__(
        self,
        user_id: uuid.UUID,
        budget_tracker_repo: repository.BudgetTrackerRepository,
        expense_source_repo: repository.ExpenseSourceRepository,
    ) -> None:
        """Construct InitializeUserWorkspaceUseCase."""
        self._user_id = user_id
        self._bt_repo = budget_tracker_repo
        self._es_repo = expense_source_repo

    def execute(self) -> None:
        """Ensure the user has default budget tracker rows and linked expense sources.

        Raises:
            WorkspaceInitializationError: If any repository operation fails.

        """
        try:
            # 1. Create missing budget tracker rows
            self._ensure_default_budget_trackers()

            # 2. Fetch all budget tracker rows again to get IDs
            all_bts = self._bt_repo.get_all()
            bt_id_by_name = {bt.name: bt.id for bt in all_bts}

            # 3. Create or update hidden expense sources
            self._ensure_hidden_expense_sources(bt_id_by_name)

        except Exception as e:
            # Catch any repository (AdapterError) or unexpected error and wrap
            msg = f"Failed to initialise workspace for user {self._user_id}: {e}"
            raise errors.DataAccessError(msg) from e

    def _ensure_default_budget_trackers(self) -> None:
        """Create any missing budget tracker rows for the user."""
        existing_bts = self._bt_repo.get_all()
        existing_names = {bt.name for bt in existing_bts}

        for name in entities.BudgetTrackerName:
            if name not in existing_names:
                bt = entities.BudgetTrackerItemModel(
                    user_id=str(self._user_id),
                    name=name,
                )
                self._bt_repo.save(bt)

    def _ensure_hidden_expense_sources(
        self,
        bt_id_by_name: dict[entities.BudgetTrackerName, uuid.UUID],
    ) -> None:
        """For each hidden budget tracker name, ensure an expense source links to it."""
        # Fetch existing expense sources for this user
        existing_es = self._es_repo.get_all()
        es_by_name = {es.name: es for es in existing_es}

        for bt_name in _HIDDEN_EXPENSE_SOURCE_BT_NAMES:
            bt_id = cast("uuid.UUID", bt_id_by_name.get(bt_name))

            expense_source_name = bt_name.value
            existing = es_by_name.get(expense_source_name)

            if existing is None:
                # Create a new expense source
                new_es = entities.ExpenseSourceModel(
                    user_id=str(self._user_id),
                    name=expense_source_name,
                    budget_tracker_ids=[bt_id],
                )
                self._es_repo.save(new_es)
            # Ensure the budget_tracker_ids list contains bt_id
            elif existing.budget_tracker_ids is None:
                existing.budget_tracker_ids = [bt_id]
            elif bt_id not in existing.budget_tracker_ids:
                existing.budget_tracker_ids.append(bt_id)
                self._es_repo.save(existing)
