"""Utility functions for handling dates and other common operations."""

import calendar
import datetime


def get_start_and_end_of_month() -> tuple[str, str]:
    """Get the start and end dates of the current month in ISO format."""
    # Get the current date
    today = datetime.datetime.now(tz=datetime.UTC).date()
    start_of_month = today.replace(day=1)
    last_day_of_month = today.replace(
        day=calendar.monthrange(today.year, today.month)[1],
    )

    # Return the start and end dates in ISO format
    return start_of_month.isoformat(), last_day_of_month.isoformat()
