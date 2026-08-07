"""Per-run isolation for the integration suite's shared "testing" database.

Every integration test hits one shared Supabase project, so two runs overlapping
in time — a stacked PR series in CI, or a local run alongside one — used to
corrupt each other. Two things kept them from coexisting: a single fixed
identity, and a teardown that emptied whole tables.

This module supplies the identity, and names the sweep that replaces the wipe:

* :data:`TEST_USER_ID` is derived per run, so one run's rows are never another's.
* :func:`stale_cutoff` bounds the sweep to rows old enough that no live run can
  own them, which is what makes cleaning up after a *crashed* run safe while
  another run is in flight.

Both are plain functions of their inputs so they can be unit-tested without a
database.
"""

import datetime
import os
import uuid
from collections.abc import Mapping

TEST_USER_PREFIX = "auth0|test-"
"""Marks a user_id as belonging to a test run, so the sweep can find them."""

STALE_AFTER = datetime.timedelta(hours=1)
"""How old a test row must be before the sweep will delete it.

Comfortably longer than a run (CI takes minutes) and comfortably shorter than
"forever", so leftovers do not accumulate in the shared project.
"""

SWEEP_TABLES = (
    "payments",
    "subscriptions",
    "quick_buttons",
    "bank_accounts",
    "joint_account_members",
)
"""Tables the sweep empties of stale test rows, in foreign-key-safe order.

``payments.bank_account_id`` and ``subscriptions.bank_account_id`` are plain
references with no ``ON DELETE`` action, so the children have to go first or the
delete is rejected.
"""


def run_user_id(
    env: Mapping[str, str] | None = None,
    token: str | None = None,
) -> str:
    """Return the ``user_id`` every row this test run writes belongs to.

    In CI the token comes from the run, so every test in the run agrees on it and
    a re-run of the same workflow gets its own. Off CI it is random, so two local
    runs — or a local run beside a CI one — still cannot collide.

    Args:
        env: The environment to read the CI run identifiers from. Defaults to the
            process environment.
        token: An explicit token, overriding both sources. For tests of this
            function.

    Returns:
        A ``user_id`` carrying :data:`TEST_USER_PREFIX`.

    """
    if token is None:
        environ = os.environ if env is None else env
        run_id = environ.get("GITHUB_RUN_ID")
        attempt = environ.get("GITHUB_RUN_ATTEMPT", "1")
        token = f"ci-{run_id}-{attempt}" if run_id else f"local-{uuid.uuid4().hex[:12]}"
    return f"{TEST_USER_PREFIX}{token}"


def stale_cutoff(now: datetime.datetime | None = None) -> str:
    """Return the timestamp before which a test row counts as abandoned.

    Args:
        now: The moment to measure back from. Defaults to the current UTC time.

    Returns:
        An ISO-8601 timestamp, ready to pass to a Postgrest ``lt`` filter.

    """
    moment = datetime.datetime.now(tz=datetime.UTC) if now is None else now
    return (moment - STALE_AFTER).isoformat()


TEST_USER_ID = run_user_id()
"""The identity this run owns. Resolved once at import, shared by every test."""
