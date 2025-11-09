"""Module for the BaseButton class."""


class BaseButton:
    """Base class for buttons."""

    def __init__(self) -> None:
        """Initialize the BaseButton instance."""
        self.css_style_normal = """
            button {
                background-color: white;
                border: 1px solid #ccc;
                color: black;
            }
            """
        self.css_style_active = """
            button {
            background-color: rgba(212, 237, 218, 0.5); /* Light green background */
            border: 1px solid #ccc;
            color: black;
            }
            """
