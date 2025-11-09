"""Utility functions for handling dates and other common operations."""

import calendar
import datetime
import re
import typing

import pandas as pd
import streamlit as st
from st_supabase_connection import SupabaseConnection


def get_start_and_end_of_month() -> tuple[str, str]:
    """Get the start and end dates of the current month in ISO format."""
    # Get the current date
    today = datetime.datetime.now(tz=datetime.UTC).date()
    start_of_month = today.replace(day=1)
    last_day_of_month = today.replace(
        day=calendar.monthrange(today.year, today.month)[1],
    )

    # Return the start and end dates in ISO format
    return start_of_month.isoformat(), last_day_of_month.isoformat()


@st.cache_data(ttl=300)
def get_column_values(
    _conn: SupabaseConnection,
    table_name: str,
    column_name: str,
) -> pd.Series[str | float | int]:
    """Get all values in a column by executing a select query."""
    response = _conn.table(table_name).select(column_name).execute()
    if response.data:
        column_data = [row[column_name] for row in response.data if column_name in row]
        return pd.Series(column_data).dropna()  # type: ignore[no-any-return]
    return pd.Series([])


@st.cache_data(ttl=60)
def get_original_data(
    _conn: SupabaseConnection,
    table_name: str,
    query_string: str,
    filters: dict[str, str | dict[str, str]] | None = None,
) -> list[dict[str, typing.Any]]:
    """Get original data by executing a select query."""
    query = _conn.table(table_name).select(query_string)
    if filters:
        for col, condition in filters.items():
            if isinstance(condition, dict):
                for op, value in condition.items():
                    query = query.filter(col, op, value)
            else:
                query = query.eq(col, condition)
    response: list[dict[str, typing.Any]] = query.execute().data
    return response or []


def enforce_unique_cols(
    conn: SupabaseConnection,
    table_name: str,
    row: dict[str, typing.Any],
    unique_columns: list[str],
) -> None:
    """Process a single row to enforce unique constraints."""
    for col in unique_columns:
        if col in row:
            unique_values = get_column_values(
                _conn=conn,
                table_name=table_name,
                column_name=col,
            )
            base_value = re.sub(r" \(\d+\)$", "", str(row[col]))
            duplicates = unique_values[unique_values.str.startswith(base_value)]
            if not duplicates.empty:
                max_suffix = (
                    duplicates.str.extract(r" \((\d+)\)$")[0].dropna().astype(int).max()
                )
                row[col] = f"{base_value} ({max_suffix + 1})"
