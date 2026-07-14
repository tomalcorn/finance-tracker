"""Unit tests for the migration CLI's database-URL selection."""

import pathlib

import pytest

from migrations import cli, discovery, errors

_PROD_URL = "postgresql://prod-host/postgres"
_TEST_URL = "postgresql://test-host/postgres"


def _migration(version: str, name: str) -> discovery.Migration:
    """Build a Migration with a throwaway path for output tests."""
    return discovery.Migration(version=version, name=name, path=pathlib.Path(name))


class TestSelectDatabaseUrl:
    """Tests for select_database_url."""

    def test_testing_env_uses_test_url(self) -> None:
        # Act
        url = cli.select_database_url("testing", _PROD_URL, _TEST_URL)
        # Assert
        assert url == _TEST_URL

    def test_prod_env_uses_prod_url(self) -> None:
        # Act
        url = cli.select_database_url("prod", _PROD_URL, _TEST_URL)
        # Assert
        assert url == _PROD_URL

    def test_missing_test_url_reports_test_variable(self) -> None:
        # Act / Assert
        with pytest.raises(errors.MissingDatabaseUrlError) as exc_info:
            cli.select_database_url("testing", _PROD_URL, None)
        assert exc_info.value.variable == "TEST_DATABASE_URL"

    def test_missing_prod_url_reports_prod_variable(self) -> None:
        # Act / Assert
        with pytest.raises(errors.MissingDatabaseUrlError) as exc_info:
            cli.select_database_url("prod", None, _TEST_URL)
        assert exc_info.value.variable == "DATABASE_URL"


class TestPrintDryRun:
    """Tests for the dry-run listing."""

    def test_lists_each_migration(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        # Arrange
        pending = [_migration("0002", "joint_workflow"), _migration("0003", "indexes")]
        # Act
        cli._print_dry_run("testing", "apply", pending)
        # Assert
        output = capsys.readouterr().out
        assert all(f"{m.version}_{m.name}" in output for m in pending)

    def test_apply_action_reads_as_would_apply(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        # Act
        cli._print_dry_run("testing", "apply", [_migration("0002", "joint_workflow")])
        # Assert
        assert "Would apply" in capsys.readouterr().out

    def test_baseline_action_reads_as_would_baseline(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        # Act
        cli._print_dry_run("prod", "baseline", [_migration("0001", "initial_schema")])
        # Assert
        assert "Would baseline" in capsys.readouterr().out

    def test_reports_nothing_to_do_when_empty(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        # Act
        cli._print_dry_run("testing", "apply", [])
        # Assert
        assert "No migrations to apply" in capsys.readouterr().out
