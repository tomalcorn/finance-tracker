"""Utility functions for handling dates and other common operations."""

import calendar
import datetime

import pandas as pd
import streamlit as st

import dataframe_handling as dfh


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


def dfe_buttons_hash_func(dfe_buttons: dfh.DFEButtons) -> str:
    """Generate a hash for the DFEButtons object."""
    return dfe_buttons.table_name


@st.cache_data(hash_funcs={dfh.DFEButtons: dfe_buttons_hash_func}, ttl=30)
def get_column_values(
    dfe_buttons: dfh.DFEButtons,
    column_name: str,
) -> pd.Series:
    """Get all values in a column by executing a select query."""
    query = dfe_buttons.table.select(column_name).execute()
    if query.data:
        column_data = [row[column_name] for row in query.data if column_name in row]
        return pd.Series(column_data).dropna()
    return pd.Series([])
