"""Use case for reading and changing one half's preferences.

A settings row is created lazily: until something is changed there is nothing
stored, and every read answers with the defaults. That keeps the workspace
initialisers out of it — no migration or seeding step has to invent a row for
every existing user — at the cost of the small dance in :meth:`load`.

The repository is ownership-scoped, so which half is being configured is
decided once, at wiring time: a ``PERSONAL`` repository loads and saves the
user's own preferences, a ``JOINT`` one the shared account's.
"""

from typing import TYPE_CHECKING

from domain import entities
from ports import errors as port_errors
from use_cases import errors

if TYPE_CHECKING:
    from ports import repository


class ManageUserSettingsUseCase:
    """Reads and updates the settings of the half it was built for."""

    def __init__(
        self,
        settings_repo: "repository.Repository[entities.UserSettingsModel]",
    ) -> None:
        """Construct ManageUserSettingsUseCase.

        Args:
            settings_repo: The settings of one ownership half, and where a
                change to them is written.

        """
        self._settings_repo = settings_repo

    def load(self) -> entities.UserSettingsModel:
        """Return the stored settings, or the defaults when none are stored yet.

        The default is built through the repository's own gate rather than
        constructed here, so it arrives already stamped with the owner and
        ownership this use case writes under — and is a complete, saveable
        entity the moment a change is made to it.

        Returns:
            The settings in force. Not necessarily persisted: a user who has
            never changed anything has no row, and gets the defaults.

        Raises:
            UserSettingsReadError: The settings could not be read, or the
                defaults could not be built.

        """
        try:
            stored = self._settings_repo.get_all()
        except port_errors.RepositoryError as e:
            msg = f"Failed to read settings: {e}"
            raise errors.UserSettingsReadError(msg) from e

        if stored:
            # One row per scope is a database invariant (0014's partial unique
            # indexes), so there is never a second one to choose between.
            return stored[0]

        try:
            return self._settings_repo.build_entities([{}])[0]
        except port_errors.RepositoryError as e:
            msg = f"Failed to build default settings: {e}"
            raise errors.UserSettingsReadError(msg) from e

    def set_income_roll_up_period(
        self,
        period: entities.IncomeRollUpPeriod,
    ) -> entities.UserSettingsModel:
        """Set the month income sources roll their payments up over.

        Writes the whole settings row, whether or not one was stored before:
        the load above hands back a complete entity either way, so the first
        change to a preference is the insert that creates the row.

        Args:
            period: The month income should be totalled over.

        Returns:
            The settings as they now stand.

        Raises:
            UserSettingsReadError: The current settings could not be read.
            UserSettingsWriteError: The change could not be persisted.

        """
        current = self.load()
        if current.income_roll_up_period is period:
            # Nothing to write, and writing anyway would bust the income and
            # budget-tracker cache entries for no change at all.
            return current

        updated = entities.UserSettingsModel.model_validate(
            current.model_copy(update={"income_roll_up_period": period}),
        )
        try:
            self._settings_repo.save_entities([updated])
        except port_errors.RepositoryError as e:
            msg = f"Failed to save the income roll-up period {period}: {e}"
            raise errors.UserSettingsWriteError(msg) from e
        return updated
