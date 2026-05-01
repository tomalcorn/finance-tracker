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
        """CSS for the normal button state (no override, use Streamlit defaults)."""
        return ""

    @property
    def css_style_active(self) -> str:
        """CSS for the active button state."""
        return """
            button {
                background-color: rgba(33, 195, 84, 0.1);
                border: 1px solid rgba(33, 195, 84, 0.3);
            }
        """
