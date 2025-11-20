"""Module for pydantic configs."""

import datetime
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
    lt: float | datetime.date | datetime.datetime | None = pydantic.Field(
        description="Less than filter value.",
        default=None,
    )
    lte: float | datetime.date | datetime.datetime | None = pydantic.Field(
        description="Less than or equal to filter value.",
        default=None,
    )
    gt: float | datetime.date | datetime.datetime | None = pydantic.Field(
        description="Greater than filter value.",
        default=None,
    )
    gte: float | datetime.date | datetime.datetime | None = pydantic.Field(
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
