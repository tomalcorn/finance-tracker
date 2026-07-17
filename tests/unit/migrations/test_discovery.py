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


class TestDiscoverForEnv:
    """Tests for discover_for_env (shared migrations plus one env overlay)."""

    def test_merges_overlay_with_shared_in_version_order(self, tmp_path: Path) -> None:
        # Arrange
        _write(tmp_path, "0001_initial_schema.sql")
        _write(tmp_path, "0003_shared_later.sql")
        overlay = tmp_path / "prod"
        overlay.mkdir()
        _write(overlay, "0002_enable_rls.sql")

        # Act
        migrations = discovery.discover_for_env(tmp_path, "prod")

        # Assert
        assert [m.version for m in migrations] == ["0001", "0002", "0003"]

    def test_excludes_other_environments_overlay(self, tmp_path: Path) -> None:
        # Arrange
        _write(tmp_path, "0001_initial_schema.sql")
        prod = tmp_path / "prod"
        prod.mkdir()
        _write(prod, "0002_enable_rls.sql")
        testing = tmp_path / "testing"
        testing.mkdir()
        _write(testing, "0003_grant_test_permissions.sql")

        # Act
        migrations = discovery.discover_for_env(tmp_path, "testing")

        # Assert
        assert [m.name for m in migrations] == [
            "initial_schema",
            "grant_test_permissions",
        ]

    def test_returns_shared_only_when_overlay_dir_absent(self, tmp_path: Path) -> None:
        # Arrange
        _write(tmp_path, "0001_initial_schema.sql")

        # Act
        migrations = discovery.discover_for_env(tmp_path, "prod")

        # Assert
        assert [m.version for m in migrations] == ["0001"]

    def test_version_reused_across_shared_and_overlay_raises(
        self,
        tmp_path: Path,
    ) -> None:
        # Arrange
        _write(tmp_path, "0002_shared.sql")
        overlay = tmp_path / "prod"
        overlay.mkdir()
        _write(overlay, "0002_enable_rls.sql")

        # Act / Assert
        with pytest.raises(errors.MigrationDiscoveryError, match="Duplicate"):
            discovery.discover_for_env(tmp_path, "prod")


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
