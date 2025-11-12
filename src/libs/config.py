"""Module for pydantic configs."""

import typing

import pydantic
import streamlit as st


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

    @pydantic.field_validator("sorting", mode="after")
    @classmethod
    def validate_sorting(cls, value: str | None) -> str | None:
        """Validate the sorting value."""
        valid_sortings = {"asc", "desc", None}
        if value not in valid_sortings:
            msg = f"Invalid sorting value: {value}. Must be one of {valid_sortings}."
            raise ValueError(msg)
        return value


test_config = DFEColumnConfig(
    column_name="example_column",
    column_config={
        "label": "Example Column",
        "disabled": True,
    },
    button_label="Example Column",
    input_widget=st.text_input,
    input_kwargs={},
    sorting=None,
    filtering=None,
    foreign_key_mapping=None,
    enforce_unique=False,
)

column_config = st.column_config.TextColumn(**test_config.column_config)

print(column_config)
