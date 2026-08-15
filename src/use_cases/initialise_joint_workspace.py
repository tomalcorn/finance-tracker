"""Joint workspace initialisation.

Seeds the root categories and the settings row for a joint account, stamping
joint ownership on every row it creates. The personal-side "Joint" root is
deliberately absent: it is the personal-side anchor for contributions,
meaningless inside the joint account itself (see #191).
"""

from typing import TYPE_CHECKING

from domain import entities
from ports import errors as port_errors
from use_cases import errors

if TYPE_CHECKING:
    import uuid

    from ports import repository

# The joint account seeds every root the personal workspace does except JOINT:
# a joint-owned copy of the personal contribution anchor would be meaningless
# and would double up the contribution model.
_JOINT_ROOT_CATEGORY_NAMES = tuple(
    name
    for name in entities.BudgetTrackerName
    if name is not entities.BudgetTrackerName.JOINT
)


class InitialiseJointWorkspaceUseCase:
    """Seeds the root categories and settings for a joint account."""

    def __init__(
        self,
        user_id: str,
        category_repo: "repository.Repository[entities.CategoryModel]",
        joint_account_repo: "repository.Repository[entities.JointAccountModel]",
        settings_repo: "repository.Repository[entities.UserSettingsModel]",
    ) -> None:
        """Construct InitialiseJointWorkspaceUseCase.

        Args:
            user_id: The member triggering the seed; stamped as ``user_id`` on
                every created row.
            category_repo: Categories repository in joint mode.
            joint_account_repo: The joint accounts the user belongs to, used to
                resolve the account id stamped on every created row.
            settings_repo: The account's settings repository in joint mode; it
                resolves the account id it stamps on the row it seeds.

        """
        self._user_id = user_id
        self._category_repo = category_repo
        self._joint_account_repo = joint_account_repo
        self._settings_repo = settings_repo

    def execute(self) -> None:
        """Ensure the user's joint account has its root categories.

        Idempotent (create-if-missing), matching the personal workspace use case.
        A user who belongs to no joint account has nothing to seed, so this is a
        no-op for them rather than a failure — unlike contributing, where the
        missing account is what the caller asked to act on.

        Raises:
            JointDataAccessError: If any repository operation fails.

        """
        try:
            account = self._resolve_joint_account()
            if account is None:
                return
            self._ensure_default_root_categories(account.id)
            self._ensure_default_settings()

        except port_errors.RepositoryError as e:
            # Wrap a persistence failure; a genuine bug propagates untouched.
            msg = f"Failed to initialise joint workspace for user {self._user_id}: {e}"
            raise errors.JointDataAccessError(msg) from e

    def _resolve_joint_account(self) -> entities.JointAccountModel | None:
        """Return the user's one joint account, or None if they belong to none."""
        accounts = self._joint_account_repo.get_all()
        return accounts[0] if accounts else None

    def _ensure_default_root_categories(self, joint_account_id: "uuid.UUID") -> None:
        """Create any missing root category for the account."""
        existing_names = {
            category.name
            for category in self._category_repo.get_all()
            if category.is_root
        }

        self._category_repo.save_entities(
            [
                entities.CategoryModel(
                    user_id=self._user_id,
                    name=name,
                    ownership_type=entities.OwnershipType.JOINT,
                    joint_account_id=joint_account_id,
                )
                for name in _JOINT_ROOT_CATEGORY_NAMES
                if name not in existing_names
            ],
        )

    def _ensure_default_settings(self) -> None:
        """Create the account's settings row at the default when none exists.

        Reached only after :meth:`_resolve_joint_account` returns an account, so
        the joint gate can resolve the id it stamps. Create-if-missing like the
        seeds above, and the joint mode of the repository stamps ownership on the
        row it builds, so the account id is not assembled here.
        """
        if self._settings_repo.get_all():
            return
        self._settings_repo.save_entities(self._settings_repo.build_entities([{}]))
