"""Module for pydantic configs."""

import typing

import pydantic
import streamlit.elements.lib.column_types as st_column_types


class DFEColumnConfig(pydantic.BaseModel):
    """Configuration for a single column in the DataFrame Editor."""

    column_name: str = pydantic.Field(
        description="The name of the column in the DataFrame.",
    )
    column_config: st_column_types.ColumnConfig = pydantic.Field(
        description="The Streamlit column configuration.",
    )
    button_label: str | None = pydantic.Field(
        description="The label for the input button.",
        default=None,
    )
    input_widget: typing.Callable = pydantic.Field(  # type: ignore[type-arg]
        description="The input widget callable from Streamlit.",
    )
    input_kwargs: dict[str, typing.Any] = pydantic.Field(
        description="The keyword arguments for the input widget.",
        default={},
    )
    sorting: typing.Literal["asc", "desc"] | None = pydantic.Field(
        description="The sorting direction for the column.",
        default=None,
    )
    filtering: str | dict[str, str] | None = pydantic.Field(
        description="The filtering criteria for the column.",
        default=None,
    )
    foreign_key_mapping: dict[str, str] | None = pydantic.Field(
        description="The mapping for foreign key relationships.",
        default=None,
    )
    enforce_unique: bool = pydantic.Field(
        description="Whether to enforce unique values in the column.",
        default=False,
    )
