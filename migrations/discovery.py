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
    """Return every migration under a directory, ordered by version.

    Files are matched against ``NNNN_description.sql``; anything else raises,
    so a mis-named file fails loudly rather than being silently skipped.

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


def pending_migrations(
    migrations: Iterable[Migration],
    applied_versions: Iterable[str],
) -> list[Migration]:
    """Return the migrations whose version is not in ``applied_versions``."""
    applied = set(applied_versions)
    return [migration for migration in migrations if migration.version not in applied]
