"""Operational tooling for the deployed finance-tracker app.

Standalone ops tooling (deliberately kept outside ``src/`` so it is clearly not
part of the app), in the same spirit as ``migrations/``. Nothing here is
imported by the Streamlit app; these modules are run by CI.
"""
