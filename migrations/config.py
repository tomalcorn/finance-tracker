"""Configuration for the migration runner, as a pydantic-settings class.

The connection string is resolved with pydantic-settings' built-in source
precedence: an explicit value (e.g. the ``--database-url`` CLI flag) wins over
an exported ``DATABASE_URL`` environment variable, which in turn wins over a
``.env`` file. Streamlit secrets are intentionally not consulted — this is
standalone ops tooling, not app code.
"""

from __future__ import annotations

import pathlib
from typing import Annotated, Literal

import pydantic
import pydantic_settings

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

    env: Annotated[
        Literal["testing", "prod"],
        pydantic.Field(description="Environment to target."),
    ] = "testing"
    database_url: Annotated[
        str,
        pydantic.Field(description="Url pointing to the SQL database for migration."),
    ]
