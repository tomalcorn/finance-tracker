"""Module for the SortButton class."""

from src.libs import config
from src.libs.buttons import base


class SortButton(base.BaseButton):
    """Class representing a sort button."""

    def __init__(
        self,
        table_name: str,
        col_configs: list[config.DFEColumnConfig],
    ) -> None:
        """Initialize the SortButton instance."""
        super().__init__()
        self._table_name = table_name
        self._col_configs = col_configs
