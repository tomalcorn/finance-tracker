"""The budget area: a master list, and one detail panel.

The block is a package because it does several distinct jobs — slicing the
category tree, describing columns, building grids, drawing the allocation panel
and drawing a tracker — and they were becoming hard to find in one file. This
module is the surface the pages use; everything else is internal to the package.
"""

from driving_adapters.blocks.budget.context import BudgetArea, BudgetTrackerSources
from driving_adapters.blocks.budget.page import commit, render

__all__ = ["BudgetArea", "BudgetTrackerSources", "commit", "render"]
