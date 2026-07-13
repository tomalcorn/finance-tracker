"""Pydantic CLI app for the migration runner (``python -m migrations``).

Replaces a hand-rolled argument parser with a pydantic-settings CLI model, so
the command-line flags, environment variables, and ``.env`` file are all read
through one settings class with built-in precedence.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import psycopg
import pydantic
import pydantic_settings

from migrations import config, discovery, errors, runner

if TYPE_CHECKING:
    from collections.abc import Sequence


class MigrateCli(config.MigrationSettings):
    """Apply versioned SQL migrations to the finance-tracker database.

    With no options, applies every pending migration. Use --status to inspect
    without changing anything, or --baseline to record all present migrations
    as applied (without running them) when adopting an existing database.
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

    status: bool = pydantic.Field(
        default=False,
        description="Show applied and pending migrations without changing anything.",
    )
    baseline: bool = pydantic.Field(
        default=False,
        description="Record all present migrations as applied without running them.",
    )

    def cli_cmd(self) -> None:
        """Entry point invoked by pydantic-settings' ``CliApp``."""
        if self.status and self.baseline:
            print("error: pass at most one of --status / --baseline", file=sys.stderr)
            raise SystemExit(2)
        try:
            database_url = self.require_database_url()
            migrations = discovery.discover_migrations(config.VERSIONS_DIR)
            with psycopg.connect(database_url) as conn:
                self._dispatch(conn, migrations)
        except (errors.MigrationError, psycopg.Error) as exc:
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
            for migration in migrations:
                runner.record_migration(conn, migration)
            print(f"Baselined {len(migrations)} migration(s) for {self.env!r}.")
            return

        if not pending:
            print(f"No pending migrations for {self.env!r}.")
            return

        for migration in pending:
            print(f"Applying {migration.version}_{migration.name} ...")
            runner.apply_migration(conn, migration)
        print(f"Applied {len(pending)} migration(s) to {self.env!r}.")


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
