"""Module for pydantic configs for the frontend models."""

import typing

import pydantic

from libs import constants

type StreamlitColumnConfig = typing.Any


class Filters(pydantic.BaseModel):
    """Model for a column filter."""

    model_config = pydantic.ConfigDict(
        serialize_by_alias=True,
    )

    eq: typing.Any | None = pydantic.Field(
        description="Equality filter value.",
        default=None,
    )
    in_: list[typing.Any] | None = pydantic.Field(
        description="In filter values.",
        serialization_alias="in",
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

    def get_pandas_filters(self) -> dict[str, typing.Any]:
        """Serialise to pandas friendly format."""
        serialised = self.model_dump(exclude_none=True)
        to_pandas_map = {
            "lt": "<",
            "lte": "<=",
            "gt": ">",
            "gte": ">=",
        }
        serialised_pandas = {}
        for key, value in serialised.items():
            if key in to_pandas_map:
                serialised_pandas[to_pandas_map[key]] = value
            else:
                serialised_pandas[key] = value
        return serialised_pandas


class DFEColumnConfig(pydantic.BaseModel):
    """Configuration for a single column in the DataFrame Editor."""

    column_name: str = pydantic.Field(
        description="The name of the column in the DataFrame.",
    )
    column_config: StreamlitColumnConfig = pydantic.Field(
        description=(
            "The Streamlit column configuration. Can be a Streamlit column_config "
            "object (TextColumn, NumberColumn, DateColumn, SelectboxColumn, etc.) "
            "or a dict representation for serialization."
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
    sorting: constants.SortingValues | None = pydantic.Field(
        description="The sorting direction for the column.",
        default=None,
    )
    filters: Filters | None = pydantic.Field(
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

    @pydantic.field_serializer("input_widget", mode="plain")
    @classmethod
    def serialize_input_widget(
        cls,
        input_widget: typing.Callable,
    ) -> str:
        """Serialize the input_widget field."""
        return input_widget.__name__

    @pydantic.field_serializer("input_kwargs", mode="plain")
    @classmethod
    def serialize_input_kwargs(
        cls,
        input_kwargs: dict[str, typing.Any],
    ) -> dict[str, typing.Any]:
        """Serialize the input_kwargs field."""
        serialised_kwargs = {}
        for key, value in input_kwargs.items():
            if callable(value):
                serialised_kwargs[key] = value.__name__
            else:
                serialised_kwargs[key] = value
        return serialised_kwargs


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
    deleted_rows: list[str] = pydantic.Field(
        description="List of row ids to be deleted.",
        default_factory=list,
    )
