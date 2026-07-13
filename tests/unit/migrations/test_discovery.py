"""Unit tests for the pure migration discovery module (no database needed)."""

from pathlib import Path

import pytest

from migrations import discovery, errors


def _write(migrations_dir: Path, name: str, sql: str = "SELECT 1;") -> Path:
    """Create a migration file and return its path."""
    path = migrations_dir / name
    path.write_text(sql, encoding="utf-8")
    return path


class TestDiscoverMigrations:
    """Tests for discover_migrations."""

    def test_orders_by_version_prefix(self, tmp_path: Path) -> None:
        _write(tmp_path, "0002_add_view.sql")
        _write(tmp_path, "0001_initial_schema.sql")
        _write(tmp_path, "0010_later.sql")

        migrations = discovery.discover_migrations(tmp_path)

        assert [m.version for m in migrations] == ["0001", "0002", "0010"]
        assert migrations[0].name == "initial_schema"

    def test_empty_directory_returns_empty_list(self, tmp_path: Path) -> None:
        assert discovery.discover_migrations(tmp_path) == []

    def test_read_sql_returns_file_contents(self, tmp_path: Path) -> None:
        _write(tmp_path, "0001_initial_schema.sql", sql="CREATE TABLE t ();")

        (migration,) = discovery.discover_migrations(tmp_path)

        assert migration.read_sql() == "CREATE TABLE t ();"

    def test_malformed_filename_raises(self, tmp_path: Path) -> None:
        _write(tmp_path, "not_a_migration.sql")

        with pytest.raises(errors.MigrationDiscoveryError, match="malformed"):
            discovery.discover_migrations(tmp_path)

    def test_duplicate_version_raises(self, tmp_path: Path) -> None:
        _write(tmp_path, "0001_initial_schema.sql")
        _write(tmp_path, "0001_duplicate.sql")

        with pytest.raises(errors.MigrationDiscoveryError, match="Duplicate"):
            discovery.discover_migrations(tmp_path)


class TestPendingMigrations:
    """Tests for pending_migrations."""

    def test_filters_out_applied_versions(self, tmp_path: Path) -> None:
        _write(tmp_path, "0001_initial_schema.sql")
        _write(tmp_path, "0002_add_view.sql")
        migrations = discovery.discover_migrations(tmp_path)

        pending = discovery.pending_migrations(migrations, applied_versions=["0001"])

        assert [m.version for m in pending] == ["0002"]

    def test_all_pending_when_nothing_applied(self, tmp_path: Path) -> None:
        _write(tmp_path, "0001_initial_schema.sql")
        migrations = discovery.discover_migrations(tmp_path)

        pending = discovery.pending_migrations(migrations, applied_versions=[])

        assert [m.version for m in pending] == ["0001"]
