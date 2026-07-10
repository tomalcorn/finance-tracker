"""Shared vocabulary to describe querying."""

import datetime
import enum
from typing import Annotated

import pydantic

type FilterValue = str | int | float | bool | datetime.date | datetime.datetime
type ColumnName = Annotated[
    str,
    pydantic.Field(description="The name of a column."),
]


class SortingValues(enum.StrEnum):
    """Sorting direction values."""

    ASC = enum.auto()
    DESC = enum.auto()


class Filters(pydantic.BaseModel):
    """Model for a column filter."""

    model_config = pydantic.ConfigDict(
        serialize_by_alias=True,
    )

    eq: Annotated[
        FilterValue | None,
        pydantic.Field(description="Equality filter value."),
    ] = None
    in_: Annotated[
        list[FilterValue] | None,
        pydantic.Field(description="In filter values.", serialization_alias="in"),
    ] = None
    lt: Annotated[
        FilterValue | None,
        pydantic.Field(description="Less than filter value."),
    ] = None
    lte: Annotated[
        FilterValue | None,
        pydantic.Field(description="Less than or equal to filter value."),
    ] = None
    gt: Annotated[
        FilterValue | None,
        pydantic.Field(description="Greater than filter value."),
    ] = None
    gte: Annotated[
        FilterValue | None,
        pydantic.Field(description="Greater than or equal to filter value."),
    ] = None
    contains: Annotated[
        str | None,
        pydantic.Field(description="Contains filter value for string matching."),
    ] = None
    cs: Annotated[
        str | None,
        pydantic.Field(description="Array contains filter value."),
    ] = None


type OptionalFilters = Annotated[
    Filters | None,
    pydantic.Field(description="Optional list of filters to apply."),
]
type OptionalSorting = Annotated[
    SortingValues | None,
    pydantic.Field(description="Optional direction in which to sort the column."),
]
