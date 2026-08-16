"""Workspace initialisation.

Seeds the budget trackers and the settings row for a user. A budget tracker is
a root category now, but it is still a budget tracker.
"""

from typing import TYPE_CHECKING

from domain import entities
from ports import errors as port_errors
from use_cases import errors

if TYPE_CHECKING:
    from ports import repository


class InitialiseUserWorkspaceUseCase:
    """Seeds a user's budget trackers and settings."""

    def __init__(
        self,
        user_id: str,
        category_repo: "repository.Repository[entities.CategoryModel]",
        settings_repo: "repository.Repository[entities.UserSettingsModel]",
    ) -> None:
        """Construct InitialiseUserWorkspaceUseCase."""
        self._user_id = user_id
        self._category_repo = category_repo
        self._settings_repo = settings_repo

    def execute(self) -> None:
        """Ensure the user has their budget trackers and settings.

        Raises:
            WorkspaceInitializationError: If any repository operation fails.

        """
        try:
            self._ensure_default_budget_trackers()
            self._ensure_default_settings()

        except port_errors.RepositoryError as e:
            # Wrap a persistence failure; a genuine bug propagates untouched.
            msg = f"Failed to initialise workspace for user {self._user_id}: {e}"
            raise errors.DataAccessError(msg) from e

    def _ensure_default_budget_trackers(self) -> None:
        """Create any missing budget tracker for the user.

        A budget tracker is a root category: the four fixed names, parented to
        nothing. Only those are seeded — everything below them is the user's
        own, and a payment can be attributed to one directly, so there is
        nothing hidden to stand in for it.
        """
        existing_names = {
            category.name
            for category in self._category_repo.get_all()
            if category.is_root
        }

        self._category_repo.save_entities(
            [
                entities.CategoryModel(user_id=self._user_id, name=name)
                for name in entities.BudgetTrackerName
                if name not in existing_names
            ],
        )

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
