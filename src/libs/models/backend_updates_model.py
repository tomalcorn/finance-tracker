"""Pydantic model for tracking pending backend mutations."""

from typing import Annotated

import pydantic

type JsonDict = dict[str, pydantic.JsonValue]


class BackendUpdates(pydantic.BaseModel):
    """Model for tracking pending creates, edits and deletes before committing."""

    added_rows: Annotated[
        list[JsonDict],
        pydantic.Field(description="List of new row data entries."),
    ] = []
    edited_rows: Annotated[
        dict[str, JsonDict],
        pydantic.Field(description="Dictionary of IDs to updated row data."),
    ] = {}
    deleted_rows: Annotated[
        list[str],
        pydantic.Field(description="List of row ids to be deleted."),
    ] = []
