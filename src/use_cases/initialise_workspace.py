"""Workspace initialisation.

Seeds default budget trackers, hidden expense sources, and the settings row for
a user.
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
    """Seeds a user's default budget trackers, expense sources, and settings."""

    def __init__(
        self,
        user_id: str,
        budget_tracker_repo: "repository.Repository[entities.BudgetTrackerItemModel]",
        expense_source_repo: "repository.Repository[entities.ExpenseSourceModel]",
        settings_repo: "repository.Repository[entities.UserSettingsModel]",
    ) -> None:
        """Construct InitialiseUserWorkspaceUseCase."""
        self._user_id = user_id
        self._bt_repo = budget_tracker_repo
        self._es_repo = expense_source_repo
        self._settings_repo = settings_repo

    def execute(self) -> None:
        """Ensure the user has default trackers, expense sources, and settings.

        Raises:
            WorkspaceInitializationError: If any repository operation fails.

        """
        try:
            self._ensure_default_budget_trackers()

            # Fetch all budget tracker rows again to get IDs
            all_bts = self._bt_repo.get_all()
            bt_id_by_name = {bt.name: bt.id for bt in all_bts}

            self._ensure_hidden_expense_sources(bt_id_by_name)
            self._ensure_default_settings()

        except port_errors.RepositoryError as e:
            # Wrap a persistence failure; a genuine bug propagates untouched.
            msg = f"Failed to initialise workspace for user {self._user_id}: {e}"
            raise errors.DataAccessError(msg) from e

    def _ensure_default_budget_trackers(self) -> None:
        """Create any missing budget tracker rows for the user."""
        existing_bts = self._bt_repo.get_all()
        existing_names = {bt.name for bt in existing_bts}

        self._bt_repo.save_entities(
            [
                entities.BudgetTrackerItemModel(user_id=self._user_id, name=name)
                for name in entities.BudgetTrackerName
                if name not in existing_names
            ],
        )

    def _ensure_hidden_expense_sources(
        self,
        bt_id_by_name: dict[entities.BudgetTrackerName, "uuid.UUID"],
    ) -> None:
        """For each hidden budget tracker name, ensure an expense source links to it."""
        # Fetch existing expense sources for this user
        existing_es = self._es_repo.get_all()
        es_by_name = {es.name: es for es in existing_es}

        to_save = []
        for bt_name in _HIDDEN_EXPENSE_SOURCE_BT_NAMES:
            bt_id = bt_id_by_name[bt_name]

            expense_source_name = bt_name.value
            existing = es_by_name.get(expense_source_name)

            if existing is None:
                to_save.append(
                    entities.ExpenseSourceModel(
                        user_id=self._user_id,
                        name=expense_source_name,
                        budget_tracker_ids=[bt_id],
                    ),
                )
            # Ensure the budget_tracker_ids list contains bt_id.
            elif existing.budget_tracker_ids is None:
                to_save.append(
                    entities.ExpenseSourceModel.model_validate(
                        existing.model_copy(update={"budget_tracker_ids": [bt_id]}),
                    ),
                )
            elif bt_id not in existing.budget_tracker_ids:
                to_save.append(
                    entities.ExpenseSourceModel.model_validate(
                        existing.model_copy(
                            update={
                                "budget_tracker_ids": [
                                    *existing.budget_tracker_ids,
                                    bt_id,
                                ],
                            },
                        ),
                    ),
                )

        self._es_repo.save_entities(to_save)

    def _ensure_default_settings(self) -> None:
        """Create the user's settings row at the default when none exists.

        Create-if-missing like the trackers above: a row already carrying a
        non-default period is left untouched, and the value seeded is the
        default, so a user who has changed nothing sees no difference. The
        default is built through the repository's gate, so ownership is stamped
        there rather than assembled here.
        """
        if self._settings_repo.get_all():
            return
        self._settings_repo.save_entities(self._settings_repo.build_entities([{}]))
