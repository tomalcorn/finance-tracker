"""Pydantic models for backend model validation."""

import enum


class SSKeys(enum.StrEnum):
    """Keys for session state management."""

    CURRENT_USER = enum.auto()
