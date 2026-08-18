"""The allocation ring: income, split between the budget trackers.

Part-to-whole at a glance. The figures themselves live on the cards beside it,
so the ring carries no legend of its own — the cards' swatches, drawn from this
module's palette, tie each one to its slice.
"""

import dataclasses
from typing import TYPE_CHECKING

import altair as alt
import pandas as pd
import streamlit as st

from domain import entities

if TYPE_CHECKING:
    from collections.abc import Sequence

    from domain import read_models

UNALLOCATED_LABEL = "Unallocated"

_CRITICAL = "#d03b3b"

_RING_INNER_RADIUS = 84

_RING_OUTER_RADIUS = 128

_ALARM_INNER_RADIUS = 136

_ALARM_OUTER_RADIUS = 141

_RING_HEIGHT = 320

_CENTRE_VALUE_SIZE = 30

_CENTRE_LABEL_SIZE = 13

_GAP_WIDTH = 2

_ALARM_GAP_WIDTH = 3


@dataclasses.dataclass(frozen=True)
class Palette:
    """The chart colours for one surface.

    Slots 1 to 4 of a validated categorical palette, stepped for their own
    surface. ``unallocated`` is achromatic so it never reads as a tracker, and
    clears 3:1 against its surface so the remainder never vanishes into it.
    """

    trackers: dict[str, str]
    unallocated: str
    surface: str
    muted: str
    text: str
    critical: str = _CRITICAL

    def tracker(self, name: str) -> str:
        """Return the slice colour for a tracker, by name."""
        return self.trackers.get(name, self.unallocated)


LIGHT = Palette(
    trackers={
        entities.BudgetTrackerName.EXPENSES: "#2a78d6",
        entities.BudgetTrackerName.JOINT: "#eb6834",
        entities.BudgetTrackerName.ONE_OFFS: "#1baf7a",
        entities.BudgetTrackerName.SAVINGS: "#eda100",
    },
    unallocated="#8a897f",
    surface="#fcfcfb",
    muted="#52514e",
    text="#0b0b0b",
)

DARK = Palette(
    trackers={
        entities.BudgetTrackerName.EXPENSES: "#3987e5",
        entities.BudgetTrackerName.JOINT: "#d95926",
        entities.BudgetTrackerName.ONE_OFFS: "#199e70",
        entities.BudgetTrackerName.SAVINGS: "#c98500",
    },
    unallocated="#7a7972",
    surface="#1a1a19",
    muted="#c3c2b7",
    text="#ffffff",
)


@dataclasses.dataclass(frozen=True)
class Slice:
    """One segment of the ring."""

    name: str
    amount: float


def palette() -> Palette:
    """Return the palette for the theme the viewer is in."""
    theme = getattr(st.context, "theme", None)
    return DARK if getattr(theme, "type", "light") == "dark" else LIGHT


def allocated(roots: "Sequence[read_models.CategoryView]") -> float:
    """Return the total budget across the trackers."""
    return sum(root.budget for root in roots)


def unallocated(roots: "Sequence[read_models.CategoryView]", income: float) -> float:
    """Return the income left over; negative once the trackers exceed it."""
    return income - allocated(roots)


def slices(
    roots: "Sequence[read_models.CategoryView]",
    income: float,
) -> list[Slice]:
    """Return the ring's segments: a tracker per budget, then any remainder.

    A tracker budgeted at nothing gets no segment. There is no remainder
    segment once the trackers have used up the income — the ring is already
    full, and the shortfall is what the alarm state reports instead.
    """
    segments = [Slice(str(root.name), root.budget) for root in roots if root.budget > 0]
    left_over = unallocated(roots, income)
    if segments and left_over > 0:
        segments.append(Slice(UNALLOCATED_LABEL, left_over))
    return segments


def render(
    roots: "Sequence[read_models.CategoryView]",
    income: float,
    colours: Palette,
) -> None:
    """Render the ring, or a caption where there is nothing to draw."""
    segments = slices(roots, income)
    if not segments:
        st.caption("Nothing allocated yet.")
        return

    over_by = -unallocated(roots, income)
    over = over_by > 0
    layers = [_arc(segments, colours, over=over)]
    if over:
        layers.append(_alarm_band(colours))
    layers += _centre(over_by if over else -over_by, colours, over=over)
    chart = (
        alt.layer(*layers)
        # Independent, or the band's single datum is stacked into the slices'
        # scale and comes out a sliver instead of a closed circle.
        .resolve_scale(theta="independent")
        .properties(height=_RING_HEIGHT)
    )
    st.altair_chart(chart, theme=None)


def _arc(
    segments: "Sequence[Slice]",
    colours: Palette,
    *,
    over: bool,
) -> "alt.Chart":
    """Build the ring itself, its slice gaps carrying the alarm colour."""
    frame = pd.DataFrame([dataclasses.asdict(segment) for segment in segments])
    domain = [segment.name for segment in segments]
    return (
        alt.Chart(frame)
        .mark_arc(
            innerRadius=_RING_INNER_RADIUS,
            outerRadius=_RING_OUTER_RADIUS,
            stroke=colours.critical if over else colours.surface,
            strokeWidth=_ALARM_GAP_WIDTH if over else _GAP_WIDTH,
        )
        .encode(
            theta=alt.Theta("amount:Q", stack=True),
            color=alt.Color(
                "name:N",
                scale=alt.Scale(
                    domain=domain,
                    range=[colours.tracker(name) for name in domain],
                ),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("name:N", title="Tracker"),
                alt.Tooltip("amount:Q", title="Budget", format=",.2f"),
            ],
        )
    )


def _alarm_band(colours: Palette) -> "alt.Chart":
    """Build the closed red band drawn around an over-allocated ring."""
    return (
        alt.Chart(pd.DataFrame({"whole": [1]}))
        .mark_arc(
            innerRadius=_ALARM_INNER_RADIUS,
            outerRadius=_ALARM_OUTER_RADIUS,
            color=colours.critical,
        )
        .encode(theta=alt.Theta("whole:Q", stack=True))
    )


def _centre(amount: float, colours: Palette, *, over: bool) -> list["alt.Chart"]:
    """Build the two lines of text that sit in the hole."""
    return [
        _centre_text(
            f"£{abs(amount):,.2f}",
            -12,
            _CENTRE_VALUE_SIZE,
            colours.critical if over else colours.text,
        ),
        _centre_text(
            "over-allocated" if over else "unallocated",
            22,
            _CENTRE_LABEL_SIZE,
            colours.muted,
        ),
    ]


def _centre_text(label: str, offset: int, size: int, colour: str) -> "alt.Chart":
    """Build one line of the centre label.

    A text mark with no positional encoding lands in the middle of the plot,
    which is the hole in the ring.
    """
    return (
        alt.Chart(pd.DataFrame({"label": [label]}))
        .mark_text(dy=offset, fontSize=size, fontWeight="bold", color=colour)
        .encode(text="label:N")
    )
