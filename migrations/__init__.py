"""Versioned SQL migration runner for the finance-tracker database.

Standalone ops tooling (deliberately kept outside ``src/`` so it is clearly not
part of the app). Applies the ordered ``versions/NNNN_description.sql`` files to
a Postgres database, recording what has run in a ``schema_migrations`` table so
re-runs only apply pending files. Invoked via ``uv run poe migrate`` — see
``migrations/README.md``.
"""
