"""Versioned SQL migration runner for the finance-tracker database.

Applies ordered ``NNNN_description.sql`` files from ``sql_stuff/migrations`` to a
Postgres database, recording what has run in a ``schema_migrations`` table so
re-runs only apply pending files. Invoked via ``uv run poe migrate`` (see
``__main__``).
"""
