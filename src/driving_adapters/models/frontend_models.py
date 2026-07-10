"""Module for pydantic configs for the frontend models."""

import typing
from collections.abc import Callable
from typing import Annotated, Any, Literal, Self

import pandas as pd
import pydantic

from domain import query
from driving_adapters.components.dfes import data_source as data_source_mod

type StreamlitColumnConfig = Any


class DFETableNameConfig(pydantic.BaseModel):
    """Configuration for a DFE table name."""

    write_table: Annotated[
        str,
        pydantic.Field(
            description="The name of the table to write (and/or read) data to.",
        ),
    ]
    key_prefix: Annotated[
        str | None,
        pydantic.Field(
            description=(
                "Prefix for Streamlit widget keys. If not provided, defaults to "
                "write_table. Use to avoid key collisions when multiple DFEs share "
                "the same underlying table."
            ),
        ),
    ] = None


class DFEColumnConfigBase(pydantic.BaseModel):
    """Base configuration for a DataFrame Editor column."""

    column_name: query.ColumnName
    column_config: Annotated[
        StreamlitColumnConfig,
        pydantic.Field(
            description=(
                "The Streamlit column configuration. Can be a Streamlit column_config "
                "object (TextColumn, NumberColumn, DateColumn, SelectboxColumn, etc.) "
                "or a dict representation for serialization."
            ),
        ),
    ]
    sorting: query.OptionalSorting = None
    filters: query.OptionalFilters = None
    visible: Annotated[
        bool,
        pydantic.Field(description="Whether to show the column in the editor."),
    ] = True
    format_func: Annotated[
        Callable[[str], str] | None,
        pydantic.Field(
            description="The formatting function for foreign key relationships.",
        ),
    ] = None
    button_label: Annotated[
        str | None,
        pydantic.Field(description="The label for the input button."),
    ] = None
    input_widget: Annotated[
        Callable[..., Any],
        pydantic.Field(description="The input widget callable from Streamlit."),
    ]
    input_kwargs: Annotated[
        dict[str, Any],
        pydantic.Field(description="The keyword arguments for the input widget."),
    ] = {}

    @pydantic.field_serializer("input_widget", "format_func", mode="plain")
    @classmethod
    def serialize_callables(
        cls,
        value: Callable,
    ) -> str:
        """Serialize the input_widget field."""
        return getattr(value, "__name__", str(value))

    @pydantic.field_serializer("input_kwargs", mode="plain")
    @classmethod
    def serialize_input_kwargs(
        cls,
        input_kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        """Serialize the input_kwargs field."""
        serialised_kwargs = {}
        for key, value in input_kwargs.items():
            if callable(value):
                serialised_kwargs[key] = getattr(value, "__name__", str(value))
            else:
                serialised_kwargs[key] = value
        return serialised_kwargs


class DFEReadOnlyColumnConfig(DFEColumnConfigBase):
    """Read-only configuration for a DataFrame Editor column."""

    @pydantic.model_validator(mode="after")
    def check_disabled_is_true(self) -> Self:
        """Validate that the column_config has disabled=True."""
        # column_config is repr as a dict
        if not isinstance(self.column_config, dict):
            msg = (
                f"Invalid column_config type: {type(self.column_config)}. "
                "Must be a dict representation of a Streamlit column config."
            )
            raise TypeError(msg)

        column_config_dict = typing.cast("dict", self.column_config)
        if (
            "disabled" in column_config_dict
            and column_config_dict["disabled"] is not True
        ):
            msg = (
                f"Read-only column '{self.column_name}' must have disabled=True in "
                f"its column_config."
            )
            raise ValueError(msg)
        return self


class DFEColumnConfig(DFEColumnConfigBase):
    """Configuration for a single column in the DataFrame Editor."""

    enforce_unique: Annotated[
        bool,
        pydantic.Field(description="Whether to enforce unique values in the column."),
    ] = False
    required: Annotated[
        bool,
        pydantic.Field(
            description="Whether this field must be filled in the add dialog.",
        ),
    ] = True


class DFEConfig(pydantic.BaseModel):
    """Full configuration for a DFE component."""

    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)

    table_names: DFETableNameConfig
    backend_model: type[pydantic.BaseModel]
    configs: list[DFEColumnConfigBase]
    sample_data: pd.DataFrame
    num_rows: Literal["fixed", "dynamic", "add", "delete"] = "delete"
    extra_row_values: dict[str, Any] | None = None
    data_source: data_source_mod.GridDataSource | None = pydantic.Field(
        default=None,
        description=(
            "Repository-backed reads for this DFE: the rows to display, plus the "
            "column values for the uniqueness rule and filter widgets. Built in "
            "composition.wiring. When omitted, the grid falls back to sample data."
        ),
    )

    @property
    def key_prefix(self) -> str:
        """The session-state / widget key prefix, defaulting to the write table."""
        return self.table_names.key_prefix or self.table_names.write_table

    @property
    def write_table(self) -> str:
        """The write table this grid targets."""
        return self.table_names.write_table

    @property
    def writable_configs(self) -> list[DFEColumnConfig]:
        """The visible, writable column configs (used by the add dialog)."""
        return [c for c in self.configs if isinstance(c, DFEColumnConfig) and c.visible]
