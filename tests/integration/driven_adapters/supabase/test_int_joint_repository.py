"""Integration tests for the joint-account and membership repositories.

Exercises the read + insert round-trip for the two joint tables against the
live "testing" connection (RLS-free, so a membership row for any user_id
inserts freely). Mirrors ``test_int_repository.py``; cache read-through is
covered separately in ``tests/unit/driving_adapters/test_cache.py``.
"""

import uuid
from collections.abc import Generator

import pytest
import st_supabase_connection

from domain import entities, read_models
from driven_adapters.supabase import repository as supabase_repos
from driving_adapters import cache

_USER_ID = "auth0|test-user-1"

type JointAccountRepo = supabase_repos.SupabaseRepository[
    entities.JointAccountModel,
    read_models.JointAccountView,
]
type MembershipRepo = supabase_repos.SupabaseRepository[
    entities.JointAccountMemberModel,
    read_models.JointAccountMemberView,
]


@pytest.fixture(name="joint_account_repo")
def _joint_account_repo(
    connection: st_supabase_connection.SupabaseConnection,
) -> JointAccountRepo:
    """Return a joint-accounts repository wired to the test connection."""
    return supabase_repos.joint_account_repository(
        _USER_ID,
        cache.StreamlitCache(),
        connection,
    )


@pytest.fixture(name="membership_repo")
def _membership_repo(
    connection: st_supabase_connection.SupabaseConnection,
) -> MembershipRepo:
    """Return a membership repository wired to the test connection."""
    return supabase_repos.joint_account_member_repository(
        _USER_ID,
        cache.StreamlitCache(),
        connection,
    )


@pytest.fixture(name="yield_joint_account")
def _yield_joint_account(
    connection: st_supabase_connection.SupabaseConnection,
) -> Generator[entities.JointAccountModel]:
    """Seed a joint account and remove it (cascading to members) afterwards."""
    account = entities.JointAccountModel(name="Test Joint Account")
    connection.table("joint_accounts").insert(
        account.model_dump(mode="json"),
    ).execute()

    yield account

    # ON DELETE CASCADE clears any membership rows created for this account.
    connection.table("joint_accounts").delete().eq(
        "id",
        str(account.id),
    ).execute()


def _account_by_id(
    repo: JointAccountRepo,
    account_id: uuid.UUID,
) -> entities.JointAccountModel | None:
    """Read a single joint account by ID."""
    matches = repo.get_by_ids([account_id])
    return matches[0] if matches else None


class TestJointAccountRepository:
    """Read + insert round-trip for joint accounts."""

    def test_saved_account_is_readable(
        self,
        joint_account_repo: JointAccountRepo,
        connection: st_supabase_connection.SupabaseConnection,
    ) -> None:
        """An account created via save is then readable by id."""
        # Arrange
        account = entities.JointAccountModel(name="Holiday Fund")

        # Act
        cache._get_data_cached.clear()
        joint_account_repo.save(account)
        cache._get_data_cached.clear()
        saved = _account_by_id(joint_account_repo, account.id)

        # Clean up
        connection.table("joint_accounts").delete().eq(
            "id",
            str(account.id),
        ).execute()
        cache._get_data_cached.clear()

        # Assert
        saved_as_expected = saved is not None and saved.name == "Holiday Fund"
        assert saved_as_expected


class TestMembershipRepository:
    """Read + insert round-trip for joint-account membership."""

    def test_saved_membership_is_listed(
        self,
        membership_repo: MembershipRepo,
        yield_joint_account: entities.JointAccountModel,
    ) -> None:
        """A membership added via save appears in get_all for the account."""
        # Arrange
        member = entities.JointAccountMemberModel(
            joint_account_id=yield_joint_account.id,
            user_id=_USER_ID,
        )

        # Act
        cache._get_data_cached.clear()
        membership_repo.save(member)
        cache._get_data_cached.clear()
        member_ids = {row.id for row in membership_repo.get_all()}

        # Assert (the joint-account fixture teardown cascades the row away)
        assert member.id in member_ids
