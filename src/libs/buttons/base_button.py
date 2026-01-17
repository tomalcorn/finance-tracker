"""Module for the BaseButton class."""


class BaseButton:
    """Base class for buttons."""

    def __init__(
        self,
        table_name: str,
    ) -> None:
        """Initialize the BaseButton instance."""
        self._table_name = table_name

    @property
    def css_style_normal(self) -> str:
        """CSS for the normal button state."""
        return """
            button {
                background-color: white;
                border: 1px solid #ccc;
                color: black;
            }
        """

    @property
    def css_style_active(self) -> str:
        """CSS for the active button state."""
        return """
            button {
                background-color: rgba(212, 237, 218, 0.5); /* Light green background */
                border: 1px solid #ccc;
                color: black;
            }
        """
