"""The allocation ring: income, split between the budget trackers.

Part-to-whole at a glance. The figures themselves live on the cards beside it,
so the ring carries no legend of its own — the cards' swatches, drawn from this
module's palette, tie each one to its slice.
"""

from typing import TYPE_CHECKING, Annotated

import altair as alt
import pandas as pd
import pydantic
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


class TrackerColours(pydantic.BaseModel):
    """A slice colour for each of the fixed budget trackers.

    A field apiece rather than a mapping: the trackers are a closed set, so a
    missing one should fail to construct rather than fall through at render
    time to the remainder's grey.
    """

    model_config = pydantic.ConfigDict(frozen=True)

    expenses: Annotated[str, pydantic.Field(description="The Expenses slice.")]
    joint: Annotated[str, pydantic.Field(description="The Joint slice.")]
    one_offs: Annotated[str, pydantic.Field(description="The One-offs slice.")]
    savings: Annotated[str, pydantic.Field(description="The Savings slice.")]

    def for_name(self, name: str) -> str | None:
        """Return the colour for a tracker, or None if it is not one of them."""
        match name:
            case entities.BudgetTrackerName.EXPENSES:
                return self.expenses
            case entities.BudgetTrackerName.JOINT:
                return self.joint
            case entities.BudgetTrackerName.ONE_OFFS:
                return self.one_offs
            case entities.BudgetTrackerName.SAVINGS:
                return self.savings
            case _:
                return None


class Palette(pydantic.BaseModel):
    """The chart colours for one surface.

    Slots 1 to 4 of a validated categorical palette, stepped for their own
    surface. ``unallocated`` is achromatic so it never reads as a tracker, and
    clears 3:1 against its surface so the remainder never vanishes into it.
    """

    model_config = pydantic.ConfigDict(frozen=True)

    trackers: Annotated[
        TrackerColours,
        pydantic.Field(description="A slice colour per budget tracker."),
    ]
    unallocated: Annotated[
        str,
        pydantic.Field(description="The remainder segment, and any unknown row."),
    ]
    surface: Annotated[
        str,
        pydantic.Field(description="The page behind the chart; the slice gaps."),
    ]
    muted: Annotated[str, pydantic.Field(description="The centre's caption.")]
    text: Annotated[str, pydantic.Field(description="The centre's figure.")]
    critical: Annotated[
        str,
        pydantic.Field(description="The alarm band, gaps and figure."),
    ] = _CRITICAL

    def tracker(self, name: str) -> str:
        """Return the slice colour for a tracker, by name."""
        colour = self.trackers.for_name(name)
        return self.unallocated if colour is None else colour


LIGHT = Palette(
    trackers=TrackerColours(
        expenses="#2a78d6",
        joint="#eb6834",
        one_offs="#1baf7a",
        savings="#eda100",
    ),
    unallocated="#8a897f",
    surface="#fcfcfb",
    muted="#52514e",
    text="#0b0b0b",
)

DARK = Palette(
    trackers=TrackerColours(
        expenses="#3987e5",
        joint="#d95926",
        one_offs="#199e70",
        savings="#c98500",
    ),
    unallocated="#7a7972",
    surface="#1a1a19",
    muted="#c3c2b7",
    text="#ffffff",
)


class Slice(pydantic.BaseModel):
    """One segment of the ring."""

    model_config = pydantic.ConfigDict(frozen=True)

    name: Annotated[str, pydantic.Field(description="The segment's label.")]
    amount: Annotated[float, pydantic.Field(description="What it is worth.")]


class Allocation(pydantic.BaseModel):
    """How an income divides between the trackers."""

    model_config = pydantic.ConfigDict(frozen=True)

    slices: Annotated[
        list[Slice],
        pydantic.Field(description="The ring's segments, in drawing order."),
    ]
    unallocated: Annotated[
        float,
        pydantic.Field(
            description="Income not yet budgeted; negative once over-allocated.",
        ),
    ]

    @property
    def is_over(self) -> bool:
        """Whether the trackers are budgeted beyond the income."""
        return self.unallocated < 0


def palette() -> Palette:
    """Return the palette for the theme the viewer is in."""
    theme = getattr(st.context, "theme", None)
    return DARK if getattr(theme, "type", "light") == "dark" else LIGHT


def allocation(
    roots: "Sequence[read_models.CategoryView]",
    income: float,
) -> Allocation:
    """Divide the income between the trackers.

    A tracker budgeted at nothing gets no slice. There is no remainder slice
    once the trackers have used up the income — the ring is already full, and
    the shortfall is what the alarm state reports instead.
    """
    left_over = income - sum(root.budget for root in roots)
    slices = [
        Slice(name=str(root.name), amount=root.budget)
        for root in roots
        if root.budget > 0
    ]
    if slices and left_over > 0:
        slices.append(Slice(name=UNALLOCATED_LABEL, amount=left_over))
    return Allocation(slices=slices, unallocated=left_over)


def render(
    roots: "Sequence[read_models.CategoryView]",
    income: float,
    colours: Palette,
) -> None:
    """Render the ring, or a caption where there is nothing to draw."""
    divided = allocation(roots, income)
    if not divided.slices:
        st.caption("Nothing allocated yet.")
        return

    over = divided.is_over
    layers = [_arc(divided.slices, colours, over=over)]
    if over:
        layers.append(_alarm_band(colours))
    layers += _centre(divided.unallocated, colours, over=over)
    chart = (
        alt.layer(*layers)
        # Independent, or the band's single datum is stacked into the slices'
        # scale and comes out a sliver instead of a closed circle.
        .resolve_scale(theta="independent")
        .properties(height=_RING_HEIGHT)
    )
    st.altair_chart(chart, theme=None)


def _arc(
    slices: "Sequence[Slice]",
    colours: Palette,
    *,
    over: bool,
) -> "alt.Chart":
    """Build the ring itself, its slice gaps carrying the alarm colour."""
    frame = pd.DataFrame([one.model_dump() for one in slices])
    domain = [one.name for one in slices]
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
