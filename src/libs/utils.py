"""Utility functions for handling dates and other common operations."""

import calendar
import datetime
import re
import typing

import pandas as pd
import streamlit as st
from st_supabase_connection import SupabaseConnection

CONN = st.connection("supabase", type=SupabaseConnection)


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
    table_name: str,
    column_name: str,
) -> pd.Series:
    """Get all values in a column by executing a select query."""
    response = CONN.table(table_name).select(column_name).execute()
    if response.data:
        column_data = [row[column_name] for row in response.data if column_name in row]
        return pd.Series(column_data).dropna()
    return pd.Series()


def get_unique_values(
    table_name: str,
    column_name: str,
) -> set[typing.Any]:
    """Get all unique values in a column by executing a select query."""
    vals = get_column_values(table_name, column_name)
    if not vals.empty:
        vals_list = vals.dropna().unique().tolist()
        return set(vals_list) if isinstance(vals_list, list) else set()
    return set()


def get_min_max_values(table_name: str, column_name: str) -> tuple[float, float]:
    """Get min and max values for numeric columns using pandas."""
    column_data = get_column_values(table_name, column_name)
    min_value = column_data.min() if not column_data.empty else 0.0
    max_value = column_data.max() if not column_data.empty else 1.0
    return (min_value, max_value)


@st.cache_data(ttl=60)
def get_original_data(
    table_name: str,
    query_string: str,
    filters: dict[str, str | dict[str, str]] | None = None,
) -> list[dict[str, typing.Any]]:
    """Get original data by executing a select query."""
    query = CONN.table(table_name).select(query_string)
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
    table_name: str,
    row: dict[str, typing.Any],
    unique_columns: list[str],
) -> None:
    """Process a single row to enforce unique constraints."""
    for col in unique_columns:
        if col in row:
            unique_values = get_column_values(
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
