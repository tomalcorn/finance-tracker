"""Module for pydantic configs."""

import typing

import pydantic
import streamlit.elements.lib.column_types as st_column_types


class DFEColumnConfig(pydantic.BaseModel):
    """Configuration for a single column in the DataFrame Editor."""

    column: str
    column_config: st_column_types.ColumnConfig
    button_label: str | None = None
    input_widget: typing.Callable
    input_kwargs: dict = {}
    sorting: typing.Literal["asc", "desc", None] = None
    filtering: str | dict[str, str] | None = None
    foreign_key_mapping: dict[str, str] | None = None
    enforce_unique: bool = False
