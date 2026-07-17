"""Pydantic CLI app for the migration runner (``python -m migrations``).

Replaces a hand-rolled argument parser with a pydantic-settings CLI model, so
the command-line flags, environment variables, and ``.env`` file are all read
through one settings class with built-in precedence.
"""

from __future__ import annotations

import pathlib
import sys
from typing import TYPE_CHECKING, Annotated, Literal

import psycopg
import pydantic
import pydantic_settings

from migrations import discovery, errors, runner

if TYPE_CHECKING:
    from collections.abc import Sequence

VERSIONS_DIR = pathlib.Path(__file__).resolve().parent / "versions"


def select_database_url(
    env: str,
    database_url: str | None,
    test_database_url: str | None,
) -> str:
    """Return the connection URL for the target environment.

    Args:
        env: The environment to target (``"testing"`` or ``"prod"``).
        database_url: The prod database URL, if configured.
        test_database_url: The testing database URL, if configured.

    Returns:
        The URL for the selected environment.

    Raises:
        MissingDatabaseUrlError: When the selected environment has no URL.

    """
    url = test_database_url if env == "testing" else database_url
    if not url:
        variable = "TEST_DATABASE_URL" if env == "testing" else "DATABASE_URL"
        raise errors.MissingDatabaseUrlError(env, variable)
    return url


class MigrateCli(pydantic_settings.BaseSettings):
    """Apply versioned SQL migrations to the finance-tracker database.

    With no options, applies every pending migration. Use --status to inspect
    applied and pending migrations, or --baseline to record all present
    migrations as applied (without running them) when adopting an existing
    database. Add --dry-run to list what apply (or --baseline) would do without
    changing anything.
    """

    model_config = pydantic_settings.SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        cli_parse_args=True,
        cli_prog_name="migrate",
        cli_kebab_case=True,
        cli_implicit_flags=True,
    )
    env: Annotated[
        Literal["testing", "prod"],
        pydantic.Field(description="Environment to target; selects which URL is used."),
    ] = "testing"
    database_url: Annotated[
        pydantic_settings.CliSuppress[str | None],
        pydantic.Field(
            description="Prod database URL (env DATABASE_URL); used when --env prod.",
        ),
    ] = None
    test_database_url: Annotated[
        pydantic_settings.CliSuppress[str | None],
        pydantic.Field(
            description=(
                "Testing database URL (env TEST_DATABASE_URL); used when --env testing."
            ),
        ),
    ] = None
    status: Annotated[
        pydantic_settings.CliImplicitFlag[bool],
        pydantic.Field(
            description=(
                "Show applied and pending migrations without changing anything."
            ),
        ),
    ] = False
    baseline: Annotated[
        pydantic_settings.CliImplicitFlag[bool],
        pydantic.Field(
            description=(
                "Record all present migrations as applied without running them."
            ),
        ),
    ] = False
    dry_run: Annotated[
        pydantic_settings.CliImplicitFlag[bool],
        pydantic.Field(
            description=(
                "List what would be applied without applying it; combine with "
                "--baseline to list what would be baselined."
            ),
        ),
    ] = False

    def cli_cmd(self) -> None:
        """Entry point invoked by pydantic-settings' ``CliApp``."""
        if self.status and (self.baseline or self.dry_run):
            print(
                "error: --status cannot be combined with --baseline / --dry-run",
                file=sys.stderr,
            )
            raise SystemExit(2)
        try:
            database_url = select_database_url(
                self.env,
                self.database_url,
                self.test_database_url,
            )
        except errors.MissingDatabaseUrlError as exc:
            print(f"error: {exc}", file=sys.stderr)
            raise SystemExit(2) from exc
        try:
            migrations = discovery.discover_for_env(VERSIONS_DIR, self.env)
            with psycopg.connect(database_url) as conn:
                self._dispatch(conn, migrations)
        except psycopg.Error as exc:
            print(f"error: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc

    def _dispatch(
        self,
        conn: psycopg.Connection,
        migrations: list[discovery.Migration],
    ) -> None:
        """Inspect or mutate the database according to the parsed options."""
        runner.ensure_tracking_table(conn)
        applied = runner.applied_versions(conn)
        pending = discovery.pending_migrations(migrations, applied)

        if self.status:
            _print_status(applied, pending)
            return

        if self.baseline:
            if self.dry_run:
                _print_dry_run(self.env, "baseline", migrations)
                return
            for migration in migrations:
                runner.record_migration(conn, migration)
            print(f"Baselined {len(migrations)} migration(s) for {self.env!r}.")
            return

        if self.dry_run:
            _print_dry_run(self.env, "apply", pending)
            return

        if not pending:
            print(f"No pending migrations for {self.env!r}.")
            return

        for migration in pending:
            print(f"Applying {migration.version}_{migration.name} ...")
            runner.apply_migration(conn, migration)
        print(f"Applied {len(pending)} migration(s) to {self.env!r}.")


def _print_dry_run(
    env: str,
    action: Literal["apply", "baseline"],
    migrations: Sequence[discovery.Migration],
) -> None:
    """Print the migrations a real ``action`` run would touch, touching none."""
    if not migrations:
        print(f"No migrations to {action} for {env!r}.")
        return
    verb, preposition = ("baseline", "for") if action == "baseline" else ("apply", "to")
    print(f"Would {verb} {len(migrations)} migration(s) {preposition} {env!r}:")
    for migration in migrations:
        print(f"  {migration.version}_{migration.name}")


def _print_status(
    applied: Sequence[str],
    pending: Sequence[discovery.Migration],
) -> None:
    """Print the applied and pending migrations to stdout."""
    print(f"Applied migrations ({len(applied)}):")
    for version in applied:
        print(f"  [x] {version}")
    print(f"Pending migrations ({len(pending)}):")
    for migration in pending:
        print(f"  [ ] {migration.version}_{migration.name}")
