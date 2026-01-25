"""Fixture for DFE instance for tests."""

import pytest

from libs.dfes import base_dfe
from libs.models import frontend_models


@pytest.fixture(name="dfe_instance")
def _dfe_instance(col_configs: list[frontend_models.DFEColumnConfig]) -> base_dfe.DFE:
    """Fixture for a DFE instance with sample user data."""
    return base_dfe.DFE(table_name="users", configs=col_configs)
