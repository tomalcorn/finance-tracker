"""Command-line entry point for the SQL migration runner.

Examples::

    uv run poe migrate                 # apply pending migrations (testing)
    uv run poe migrate --env prod      # apply pending migrations (prod)
    uv run poe migrate --status        # show applied / pending, change nothing
    uv run poe migrate --baseline      # mark all present migrations as applied
"""

from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING

import psycopg

from driven_adapters.migrations import config, discovery, errors, runner

if TYPE_CHECKING:
    from collections.abc import Sequence

_DEFAULT_ENV = "testing"


def _build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the migrate command."""
    parser = argparse.ArgumentParser(
        prog="migrate",
        description="Apply versioned SQL migrations to the finance-tracker DB.",
    )
    parser.add_argument(
        "--env",
        default=_DEFAULT_ENV,
        help="Target environment, used to resolve the DB URL (default: %(default)s).",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--status",
        action="store_true",
        help="Show applied and pending migrations without changing anything.",
    )
    mode.add_argument(
        "--baseline",
        action="store_true",
        help="Record all present migrations as applied without running them.",
    )
    return parser


def _print_status(
    applied: list[str],
    pending: list[discovery.Migration],
) -> None:
    """Print the applied and pending migrations to stdout."""
    print(f"Applied migrations ({len(applied)}):")
    for version in applied:
        print(f"  [x] {version}")
    print(f"Pending migrations ({len(pending)}):")
    for migration in pending:
        print(f"  [ ] {migration.version}_{migration.name}")


def _run(
    conn: psycopg.Connection,
    args: argparse.Namespace,
    migrations: list[discovery.Migration],
) -> None:
    """Inspect or mutate the database according to the parsed arguments."""
    runner.ensure_tracking_table(conn)
    applied = runner.applied_versions(conn)
    pending = discovery.pending_migrations(migrations, applied)

    if args.status:
        _print_status(applied, pending)
        return

    if args.baseline:
        for migration in migrations:
            runner.record_migration(conn, migration)
        print(f"Baselined {len(migrations)} migration(s) for {args.env!r}.")
        return

    if not pending:
        print(f"No pending migrations for {args.env!r}.")
        return

    for migration in pending:
        print(f"Applying {migration.version}_{migration.name} ...")
        runner.apply_migration(conn, migration)
    print(f"Applied {len(pending)} migration(s) to {args.env!r}.")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the migrate command and return a process exit code."""
    args = _build_parser().parse_args(argv)
    try:
        migrations = discovery.discover_migrations(config.MIGRATIONS_DIR)
        database_url = config.resolve_database_url(args.env)
        with psycopg.connect(database_url) as conn:
            _run(conn, args, migrations)
    except (errors.MigrationError, psycopg.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
