"""Fixture for DFE instance for tests."""

import pandas as pd
import pydantic
import pytest

from libs.dfes import base_dfe
from libs.models import frontend_models


class _StubModel(pydantic.BaseModel):
    pass


@pytest.fixture(name="dfe_instance")
def _dfe_instance(
    col_configs: list[frontend_models.DFEColumnConfigBase],
) -> base_dfe.DFE:
    """Fixture for a DFE instance with sample user data."""
    return base_dfe.DFE(
        config=frontend_models.DFEConfig(
            table_names=frontend_models.DFETableNameConfig(write_table="users"),
            backend_model=_StubModel,
            configs=col_configs,
            sample_data=pd.DataFrame(),
        ),
    )
