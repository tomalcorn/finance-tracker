"""Configuration for the migration runner, as a pydantic-settings class.

The connection string is resolved with pydantic-settings' built-in source
precedence: an explicit value (e.g. the ``--database-url`` CLI flag) wins over
an exported ``DATABASE_URL`` environment variable, which in turn wins over a
``.env`` file. Streamlit secrets are intentionally not consulted — this is
standalone ops tooling, not app code.
"""

from __future__ import annotations

import pathlib

import pydantic_settings

from migrations import errors

# This file is migrations/config.py, so the SQL files live alongside it in
# migrations/versions/.
VERSIONS_DIR = pathlib.Path(__file__).resolve().parent / "versions"


class MigrationSettings(pydantic_settings.BaseSettings):
    """Connection configuration for the migration runner."""

    model_config = pydantic_settings.SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = "testing"
    database_url: str | None = None

    def require_database_url(self) -> str:
        """Return the connection string, or raise if it was never configured.

        Raises:
            MigrationConfigError: If no database URL was provided via CLI flag,
                environment variable, or ``.env`` file.

        """
        if not self.database_url:
            msg = (
                "No database URL configured. Pass --database-url, export "
                "DATABASE_URL, or add DATABASE_URL to a .env file."
            )
            raise errors.MigrationConfigError(msg)
        return self.database_url
