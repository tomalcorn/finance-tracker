"""Pure discovery and ordering of on-disk SQL migration files.

Deliberately free of any database or Streamlit dependency, so the filename
rules and ordering can be unit-tested in isolation.
"""

from __future__ import annotations

import dataclasses
import re
from typing import TYPE_CHECKING

from migrations import errors

if TYPE_CHECKING:
    import pathlib
    from collections.abc import Iterable

# NNNN_lower_snake_name.sql — a 4-digit version prefix and a snake_case name.
_FILENAME_PATTERN = re.compile(r"^(?P<version>\d{4})_(?P<name>[a-z0-9_]+)\.sql$")


@dataclasses.dataclass(frozen=True)
class Migration:
    """A single migration file discovered on disk."""

    version: str
    name: str
    path: pathlib.Path

    def read_sql(self) -> str:
        """Return the SQL text contained in this migration file."""
        return self.path.read_text(encoding="utf-8")


def discover_migrations(migrations_dir: pathlib.Path) -> list[Migration]:
    """Return every migration directly under a directory, ordered by version.

    Only ``.sql`` files sitting directly in ``migrations_dir`` are considered;
    the glob does not recurse, so per-environment overlay subdirectories
    (``versions/prod``, ``versions/testing``) are ignored here and gathered by
    :func:`discover_for_env` instead. Files are matched against
    ``NNNN_description.sql``; anything else raises, so a mis-named file fails
    loudly rather than being silently skipped.

    Raises:
        MigrationDiscoveryError: If a ``.sql`` filename is malformed or two
            files share the same version prefix.

    """
    migrations: list[Migration] = []
    seen: dict[str, pathlib.Path] = {}
    for path in sorted(migrations_dir.glob("*.sql")):
        match = _FILENAME_PATTERN.match(path.name)
        if match is None:
            msg = (
                f"Migration filename {path.name!r} is malformed; expected "
                f"'NNNN_description.sql' (4-digit version, lower_snake name)."
            )
            raise errors.MigrationDiscoveryError(msg)
        version = match.group("version")
        if version in seen:
            msg = (
                f"Duplicate migration version {version!r}: "
                f"{seen[version].name} and {path.name}."
            )
            raise errors.MigrationDiscoveryError(msg)
        seen[version] = path
        migrations.append(
            Migration(version=version, name=match.group("name"), path=path),
        )
    return migrations


def discover_for_env(versions_dir: pathlib.Path, env: str) -> list[Migration]:
    """Return the shared migrations plus one environment's overlay, ordered.

    Shared migrations live directly in ``versions_dir`` and apply to every
    environment. Environment-specific ones live in a ``versions_dir/<env>``
    subdirectory and apply only when targeting that environment (RLS policies
    for ``prod``, role grants for ``testing``). The shared set and the overlay
    share a single version sequence, so a version reused across them raises
    rather than one silently shadowing the other.

    Args:
        versions_dir: The directory holding the shared migrations and the
            per-environment overlay subdirectories.
        env: The environment being targeted (``"testing"`` or ``"prod"``).

    Raises:
        MigrationDiscoveryError: If a filename is malformed, or a version is
            reused between the shared set and the overlay.

    """
    shared = discover_migrations(versions_dir)
    overlay_dir = versions_dir / env
    if not overlay_dir.is_dir():
        return shared
    overlay = discover_migrations(overlay_dir)

    seen: dict[str, Migration] = {}
    for migration in (*shared, *overlay):
        existing = seen.get(migration.version)
        if existing is not None:
            msg = (
                f"Duplicate migration version {migration.version!r}: "
                f"{existing.path.name} and {migration.path.name}."
            )
            raise errors.MigrationDiscoveryError(msg)
        seen[migration.version] = migration
    return sorted(seen.values(), key=lambda migration: migration.version)


def pending_migrations(
    migrations: Iterable[Migration],
    applied_versions: Iterable[str],
) -> list[Migration]:
    """Return the migrations whose version is not in ``applied_versions``."""
    applied = set(applied_versions)
    return [migration for migration in migrations if migration.version not in applied]
