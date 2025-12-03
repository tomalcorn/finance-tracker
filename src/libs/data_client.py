"""Module for handling interactions with Supabase backend."""

import typing

import pandas as pd
import st_supabase_connection
import streamlit as st

from libs import constants, frontend_models

CONN = st.connection("supabase", type=st_supabase_connection.SupabaseConnection)


@st.cache_data(ttl=300)
def _execute_query(
    query: st_supabase_connection.SyncSelectRequestBuilder,
) -> list[dict[str, typing.Any]]:
    """Execute the given query and return the data."""
    response = query.execute()
    return response.data or []


class DataClient:
    """Class for interacting with the Supabase backend."""

    def __init__(self, connection: st_supabase_connection.SupabaseConnection) -> None:
        """Initialize the DataClient with Supabase credentials."""
        self._conn = connection

    def _apply_filters_to_query(
        self,
        query: st_supabase_connection.SyncSelectRequestBuilder,
        config: frontend_models.DFEColumnConfig,
    ) -> st_supabase_connection.SyncSelectRequestBuilder:
        """Apply filters from column configurations to the query."""
        if config.filtering:
            for filter_key, filter_value in config.filtering.model_dump(
                exclude_none=True,
            ).items():
                query = query.filter(config.column_name, filter_key, filter_value)
        return query

    def _apply_sorting_to_query(
        self,
        query: st_supabase_connection.SyncSelectRequestBuilder,
        config: frontend_models.DFEColumnConfig,
    ) -> st_supabase_connection.SyncSelectRequestBuilder:
        """Apply sorting from column configurations to the query."""
        if config.sorting:
            query = query.order(
                config.column_name,
                desc=config.sorting == constants.SortingValues.DESCENDING,
            )
        return query

    def get_data(
        self,
        table_name: str,
        query_string: str,
        configs: list[frontend_models.DFEColumnConfig] | None = None,
    ) -> list[dict[str, typing.Any]]:
        """Fetch data from the specified table with optional filters."""
        query = self._conn.table(table_name).select(query_string)
        if configs:
            for config in configs:
                query = self._apply_filters_to_query(query, config)
                query = self._apply_sorting_to_query(query, config)
        return _execute_query(query)

    def get_column_values(
        self,
        table_name: str,
        column_name: str,
        *,
        unique: bool = False,
    ) -> pd.Series:
        """Get all values in a column by executing a select query."""
        query = self._conn.table(table_name).select(column_name)
        response = _execute_query(query)
        if not response:
            return pd.Series()
        all_col_values = pd.Series(
            [row[column_name] for row in response if column_name in row],
        ).dropna()
        if unique:
            return all_col_values.drop_duplicates().reset_index(drop=True)
        return all_col_values.reset_index(drop=True)
