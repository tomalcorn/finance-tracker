"""Utility functions for handling dates and other common operations."""

import contextlib
import re
import typing

import streamlit as st
from st_supabase_connection import SupabaseConnection

from apps import data_client

CONN = st.connection("supabase", type=SupabaseConnection)


# To be removed in #25
def enforce_unique_cols(
    table_name: str,
    row: dict[str, typing.Any],
    unique_columns: list[str],
) -> None:
    """Process a single row to enforce unique constraints."""
    for col in unique_columns:
        if col in row:
            unique_values = set(
                data_client.get_column_values(
                    table_name=table_name,
                    column_name=col,
                    unique=True,
                ),
            )
            base_value = re.sub(r" \(\d+\)$", "", str(row[col]))
            # Filter unique_values for entries that start with base_value
            duplicates = [
                str(v) for v in unique_values if str(v).startswith(base_value)
            ]
            if duplicates:
                # Extract numeric suffixes like " (123)" and take the max; if none
                # found, start from 0
                suffixes = []
                for val in duplicates:
                    match = re.search(r" \((\d+)\)$", val)
                    if match:
                        with contextlib.suppress(ValueError):
                            suffixes.append(int(match.group(1)))
                max_suffix = max(suffixes) if suffixes else 0
                row[col] = f"{base_value} ({max_suffix + 1})"
