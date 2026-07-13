"""Resolve the migration runner's database URL and migrations directory.

The connection string is resolved in this order (first match wins):

1. The ``DATABASE_URL`` environment variable.
2. ``[migrations].<env>_db_url`` in ``.streamlit/secrets.toml``.
3. ``[supabase_admin].db_url`` in ``.streamlit/secrets.toml``.
"""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from driven_adapters.migrations import errors

# This file is src/driven_adapters/migrations/config.py, so the repo root is
# four levels up; the migration files live under sql_stuff/migrations there.
_REPO_ROOT = Path(__file__).resolve().parents[3]
MIGRATIONS_DIR = _REPO_ROOT / "sql_stuff" / "migrations"

_ENV_VAR = "DATABASE_URL"


def resolve_database_url(env: str) -> str:
    """Return the Postgres connection string for the given environment.

    Raises:
        MigrationConfigError: If no connection string can be resolved from the
            environment or Streamlit secrets.

    """
    from_env = os.environ.get(_ENV_VAR)
    if from_env:
        return from_env

    from_secrets = _url_from_secrets(env)
    if from_secrets:
        return from_secrets

    msg = (
        f"No database URL for environment {env!r}. Set the {_ENV_VAR} environment "
        f"variable, or add [migrations].{env}_db_url (or [supabase_admin].db_url) "
        f"to .streamlit/secrets.toml."
    )
    raise errors.MigrationConfigError(msg)


def _url_from_secrets(env: str) -> str | None:
    """Return a DB URL from Streamlit secrets, or None if it is unavailable.

    Any failure to read secrets (no file, missing keys) is treated as "not
    configured" so the caller can fall back to a clear configuration error.
    """
    try:
        migrations_section = st.secrets.get("migrations", {})
        env_url = migrations_section.get(f"{env}_db_url")
        if env_url:
            return str(env_url)

        admin_section = st.secrets.get("supabase_admin", {})
        admin_url = admin_section.get("db_url")
    except Exception:  # noqa: BLE001 - absent/invalid secrets means "not configured"
        return None
    else:
        return str(admin_url) if admin_url else None
