"""Module for pydantic configs for the frontend models."""

import typing

import pydantic


class Filters(pydantic.BaseModel):
    """Model for a column filter."""

    eq: typing.Any | None = pydantic.Field(
        description="Equality filter value.",
        default=None,
    )
    in_: list[typing.Any] | None = pydantic.Field(
        description="In filter values.",
        alias="in",
        default=None,
    )
    lt: typing.Any | None = pydantic.Field(
        description="Less than filter value.",
        default=None,
    )
    lte: typing.Any | None = pydantic.Field(
        description="Less than or equal to filter value.",
        default=None,
    )
    gt: typing.Any | None = pydantic.Field(
        description="Greater than filter value.",
        default=None,
    )
    gte: typing.Any | None = pydantic.Field(
        description="Greater than or equal to filter value.",
        default=None,
    )
    contains: str | None = pydantic.Field(
        description="Contains filter value for string matching.",
        default=None,
    )


class DFEColumnConfig(pydantic.BaseModel):
    """Configuration for a single column in the DataFrame Editor."""

    column_name: str = pydantic.Field(
        description="The name of the column in the DataFrame.",
    )
    column_config: dict[str, typing.Any] = pydantic.Field(
        description=(
            "The Streamlit column configuration. Needs to be converted from streamlit "
            "column_config objects to dictionaries due to type checking problems. "
            "Needs to be converted back to streamlit column_config objects before use."
        ),
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
    sorting: str | None = pydantic.Field(
        description="The sorting direction for the column.",
        default=None,
    )
    filtering: Filters | None = pydantic.Field(
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

    @pydantic.field_validator("sorting", mode="after")
    @classmethod
    def validate_sorting(cls, value: str | None) -> str | None:
        """Validate the sorting value."""
        valid_sortings = {"asc", "desc", None}
        if value not in valid_sortings:
            msg = f"Invalid sorting value: {value}. Must be one of {valid_sortings}."
            raise ValueError(msg)
        return value


class BackendUpdates(pydantic.BaseModel):
    """Model for backend updates tracking."""

    added_rows: list[dict[str, typing.Any]] = pydantic.Field(
        description="List of new row data entries.",
        default_factory=list,
    )
    edited_rows: dict[str, dict[str, typing.Any]] = pydantic.Field(
        description="Dictionary of IDs to updated row data.",
        default_factory=dict,
    )
    deleted_rows: list[dict[str, typing.Any]] = pydantic.Field(
        description="List of row data entries to be deleted.",
        default_factory=list,
    )
    row_ids: list[str] = pydantic.Field(
        description="List of all row IDs currently tracked.",
        default_factory=list,
    )
    prev_added_rows: list[dict[str, typing.Any]] = pydantic.Field(
        description="List of previously added row data entries.",
        default_factory=list,
    )
