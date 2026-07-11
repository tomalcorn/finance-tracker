"""Pydantic configs for the grid (DataFrame-editor) frontend.

The grid config is split into two ontologically distinct halves so a function
can ask for the slice it needs instead of the whole god-object:

- ``GridSource`` — how a grid persists and is identified: the data port, the
  write table (and widget-key prefix), the add-dialog backend model, and any
  extra row values. The *source* half.
- ``GridDisplay`` — what a grid shows: its columns, row-edit mode, and the
  empty-state sample frame. The *display* half.

``DFEConfig`` composes the two for the top-level orchestrators (``render`` /
``commit`` / ``build_working_df``) that legitimately need both; leaf functions
take only ``GridSource`` or ``GridDisplay``.

Column roles are flags on one ``DFEColumnConfig``, not a subclass hierarchy:
``editable=False`` marks a read-only view column; ``enforce_unique`` / ``required``
apply to editable columns in the add dialog.
"""

import typing
from collections.abc import Callable
from typing import Annotated, Any, Literal, Self

import pandas as pd
import pydantic

from domain import query
from driving_adapters.components.dfes import data_source as data_source_mod

type StreamlitColumnConfig = Any


class DFEColumnConfig(pydantic.BaseModel):
    """Configuration for a single column in the DataFrame editor.

    The column's role is expressed by flags rather than a subclass: an
    ``editable=False`` column is read-only (and must carry ``disabled=True`` in
    its Streamlit ``column_config``); ``enforce_unique`` and ``required`` govern
    an editable column's behaviour in the add dialog.
    """

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
    editable: Annotated[
        bool,
        pydantic.Field(
            description=(
                "Whether the column can be edited. A read-only (editable=False) "
                "column is a computed/view column and must set disabled=True in its "
                "column_config; it is skipped by the add dialog and uniqueness rules."
            ),
        ),
    ] = True
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

    @pydantic.model_validator(mode="after")
    def check_read_only_is_disabled(self) -> Self:
        """Validate that a read-only column's column_config has disabled=True."""
        if self.editable:
            return self
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


class GridSource(pydantic.BaseModel):
    """How a grid persists and is identified (the *source* half of a grid).

    Bundles the read/write data port with the write target and add-dialog
    wiring, so reads, writes, and filters can each ask for this one coherent
    slice instead of the whole config.
    """

    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)

    write_table: Annotated[
        str,
        pydantic.Field(
            description="The name of the table to write (and/or read) data to.",
        ),
    ]
    key_prefix_override: Annotated[
        str | None,
        pydantic.Field(
            description=(
                "Prefix for Streamlit widget keys. Defaults to write_table. Set to "
                "avoid key collisions when multiple grids share one table."
            ),
        ),
    ] = None
    backend_model: Annotated[
        type[pydantic.BaseModel],
        pydantic.Field(description="The write model rows are validated against."),
    ]
    extra_row_values: Annotated[
        dict[str, Any] | None,
        pydantic.Field(
            description="Fixed values merged into every row added via the dialog.",
        ),
    ] = None
    data_source: data_source_mod.GridDataSource | None = pydantic.Field(
        default=None,
        description=(
            "Repository-backed reads for this grid: the rows to display, plus the "
            "column values for the uniqueness rule and filter widgets. Built in "
            "composition.wiring. When omitted, the grid falls back to sample data."
        ),
    )

    @property
    def key_prefix(self) -> str:
        """The session-state / widget key prefix, defaulting to the write table."""
        return self.key_prefix_override or self.write_table


class GridDisplay(pydantic.BaseModel):
    """What a grid shows (the *display* half of a grid)."""

    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)

    columns: Annotated[
        list[DFEColumnConfig],
        pydantic.Field(description="The ordered column configs for the editor."),
    ]
    num_rows: Literal["fixed", "dynamic", "add", "delete"] = "delete"
    sample_data: Annotated[
        pd.DataFrame,
        pydantic.Field(description="Frame shown when the data source read is empty."),
    ]

    @property
    def writable_columns(self) -> list[DFEColumnConfig]:
        """The visible, editable columns (used by the add dialog)."""
        return [c for c in self.columns if c.editable and c.visible]


class DFEConfig(pydantic.BaseModel):
    """A full grid config: its source and display halves.

    Held by the top-level orchestrators (``render`` / ``commit`` /
    ``build_working_df``) that need both halves; leaf functions take
    ``source`` or ``display`` directly.
    """

    source: GridSource
    display: GridDisplay

    @property
    def key_prefix(self) -> str:
        """The grid's widget-key prefix (delegated to the source)."""
        return self.source.key_prefix
