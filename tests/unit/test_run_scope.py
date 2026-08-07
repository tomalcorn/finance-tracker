"""Tests for the integration suite's per-run isolation (#221).

These guard the two properties the shared testing database depends on: one run's
rows can never be mistaken for another's, and the stale-row sweep can never reach
a live run's rows.
"""

import datetime

from tests import run_scope


class TestRunUserId:
    """The identity every row a run writes belongs to."""

    def test_a_ci_run_derives_one_identity(self) -> None:
        # Arrange - every test in a run must agree, or the fixtures and the
        # teardown scope themselves to different users
        env = {"GITHUB_RUN_ID": "42", "GITHUB_RUN_ATTEMPT": "1"}

        # Act
        first, second = run_scope.run_user_id(env), run_scope.run_user_id(env)

        # Assert
        assert first == second

    def test_a_re_run_gets_its_own_identity(self) -> None:
        # Arrange - a re-run overlaps the original's leftovers, so it must not
        # inherit its rows
        first_attempt = {"GITHUB_RUN_ID": "42", "GITHUB_RUN_ATTEMPT": "1"}
        second_attempt = {"GITHUB_RUN_ID": "42", "GITHUB_RUN_ATTEMPT": "2"}

        # Act
        first = run_scope.run_user_id(first_attempt)
        second = run_scope.run_user_id(second_attempt)

        # Assert
        assert first != second

    def test_two_local_runs_cannot_collide(self) -> None:
        # Arrange - off CI there is no run id to derive from, so the token is
        # random; a local run beside a CI one must still be isolated

        # Act
        first, second = run_scope.run_user_id({}), run_scope.run_user_id({})

        # Assert
        assert first != second

    def test_the_identity_is_sweepable(self) -> None:
        # Arrange - the sweep finds test rows by this prefix, so an identity
        # without it would leak rows that nothing ever cleans up
        env = {"GITHUB_RUN_ID": "42"}

        # Act
        user_id = run_scope.run_user_id(env)

        # Assert
        assert user_id.startswith(run_scope.TEST_USER_PREFIX)


class TestStaleCutoff:
    """The age bound that keeps the sweep off a live run's rows."""

    def test_the_cutoff_predates_the_moment_it_is_taken_from(self) -> None:
        # Arrange
        now = datetime.datetime(2026, 8, 7, 12, 0, tzinfo=datetime.UTC)

        # Act
        cutoff = run_scope.stale_cutoff(now)

        # Assert - a row written during this run is newer than the cutoff, so the
        # sweep's `lt` filter cannot match it
        assert datetime.datetime.fromisoformat(cutoff) < now

    def test_the_cutoff_leaves_room_for_a_whole_run(self) -> None:
        # Arrange - a run takes minutes; the bound has to be comfortably longer
        # than the slowest one
        now = datetime.datetime(2026, 8, 7, 12, 0, tzinfo=datetime.UTC)

        # Act
        cutoff = run_scope.stale_cutoff(now)

        # Assert
        age = now - datetime.datetime.fromisoformat(cutoff)
        assert age >= datetime.timedelta(minutes=30)


def test_children_are_swept_before_their_parents() -> None:
    # Arrange - payments and subscriptions reference bank_accounts with no
    # ON DELETE action, so deleting the accounts first is rejected outright
    tables = run_scope.SWEEP_TABLES

    # Act
    accounts_at = tables.index("bank_accounts")

    # Assert
    assert all(
        [
            tables.index("payments") < accounts_at,
            tables.index("subscriptions") < accounts_at,
            tables.index("quick_buttons") < accounts_at,
        ],
    )
