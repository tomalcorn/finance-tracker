"""Explicit column widths for the grids that carry a totals strip.

Streamlit sizes a column to its content, and the strip is a second table below
the grid: the two only line up if both are told the same widths. So a grid with
totals declares a width for every visible column — enforced by a validator on
``GridDisplay`` — and the strip inherits them.

These are *base* widths in pixels. Both tables still stretch to fill their
container, sharing whatever space is left over equally, so the numbers set the
proportions between columns rather than the final size.
"""

NAME = 160
"""A row's name, the widest text a grid usually shows."""

MONEY = 115
"""An amount in pounds."""

PROGRESS = 110
"""A percentage bar (progress, split)."""

DATE = 105
"""A localised date."""

SELECT = 135
"""A foreign key shown as its target's name."""

CADENCE = 100
"""A subscription's cadence."""

FLAG = 75
"""A checkbox."""
