"""Apply pending SQL migrations against a Postgres database.

Each applied migration is recorded in a ``schema_migrations`` table so that a
re-run executes only the files that have not yet been applied. Applying a
migration and recording it share one transaction, so a failure leaves neither
the schema change nor the tracking row behind.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import psycopg

    from migrations.discovery import Migration

_CREATE_TRACKING_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

_SELECT_VERSIONS = "SELECT version FROM schema_migrations ORDER BY version;"

_INSERT_VERSION = "INSERT INTO schema_migrations (version, name) VALUES (%s, %s);"

_INSERT_VERSION_IF_ABSENT = (
    "INSERT INTO schema_migrations (version, name) VALUES (%s, %s) "
    "ON CONFLICT (version) DO NOTHING;"
)


def ensure_tracking_table(conn: psycopg.Connection) -> None:
    """Create the ``schema_migrations`` table if it does not already exist."""
    with conn.cursor() as cur:
        cur.execute(_CREATE_TRACKING_TABLE)
    conn.commit()


def applied_versions(conn: psycopg.Connection) -> list[str]:
    """Return the versions recorded in ``schema_migrations``, ascending."""
    with conn.cursor() as cur:
        cur.execute(_SELECT_VERSIONS)
        return [row[0] for row in cur.fetchall()]


def apply_migration(conn: psycopg.Connection, migration: Migration) -> None:
    """Run one migration's SQL and record it, atomically."""
    with conn.transaction(), conn.cursor() as cur:
        # Migration text is trusted, developer-authored SQL. It is passed as
        # bytes (rather than str) so psycopg runs the whole file via the simple
        # query protocol, which allows the multiple statements a file contains.
        cur.execute(migration.read_sql().encode("utf-8"))
        cur.execute(_INSERT_VERSION, (migration.version, migration.name))


def record_migration(conn: psycopg.Connection, migration: Migration) -> None:
    """Record a migration as applied WITHOUT running its SQL (baselining)."""
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(_INSERT_VERSION_IF_ABSENT, (migration.version, migration.name))
