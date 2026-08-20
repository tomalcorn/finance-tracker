---
front_matter_title: Budget Tracker
slug: budget_tracker
order: 3
icon: ":material/pie_chart:"
---
# Budget Tracker

The budget tracker is the top-level allocation layer in the app. It answers:

- how much budget each category has
- how much of that budget has been used this month
- how much remains
- how that category is split across your income

## The Page

A list down the left, and one panel on the right showing whatever you pick from
it. The list runs in the order the decisions happen in: what came in, how it is
split, then what each split is being spent on.

### Income

Where your income sources live — see [Income Sources](#income-sources) below.

### Budget Trackers

The allocation panel: **the one place a tracker's monthly budget is set**. A
card for each of the fixed trackers that act as your main buckets:

- Expenses
- Joint
- One-offs
- Savings

These rows are fixed because they anchor the rest of the model. Categories sit
beneath them, income sources point at them, and everything rolls up into them.

Beside the cards is a ring of your income, split between the trackers, with the
unallocated remainder in grey and its figure in the middle. Allocate more than
you earn and the ring turns red.

### One Tracker At A Time

Picking a tracker shows its figures and, underneath, the categories beneath it.
`Expenses` is usually where you model spending like groceries, transport, rent,
or other regular monthly payments; `One-offs` holds savings goals, and behaves
differently enough to have [its own page](/one_offs).

`Joint` and `Savings` are each a single pot of money, so neither is broken down
into categories.

A tracker's own budget is read-only here — it is set on **Budget Trackers**, so
that one number has one home.

A payment only counts toward a category if you attribute it to one, so leaving a
payment uncategorised keeps it out of these totals — see
[getting paid back and moving money between accounts](/payments) for the two
cases where that matters.

You can attribute a payment to a budget tracker directly as well as to one of
its expense categories. Spending booked straight onto `Expenses` still counts
toward that tracker's total; it just isn't broken down any further.

### Income Sources

Income sources are the mirror image for inflows. They show how much income was
received in the roll-up month and which budget tracker rows that income
supports.

Not every inflow belongs here. Money someone owes you back can be recorded as
income against its own source *or* as a negative expense that offsets the
original category — [Payments](/payments) explains when to reach for each.

By default the roll-up month is the current one. If you are paid at the end of
the month, so that each month runs on the previous month's pay, you can move the
income roll-up back a month in [Settings](/settings) — the column then reads
`Received Last Month`, and the allocation ring is split against it. Spending
stays on the current month either way. Personal and joint are set separately.

## How The Links Work

Income sources say which budget tracker rows the income contributes toward.
Categories work the other way round: each one sits under the budget tracker you
added it beneath, and its spending rolls up into that tracker's `Spent`.

## How To Read The Page

- If `Budget used` is near 100%, that tracker is close to or at its budget; the
  same goes for `% Spent` on one of its categories.
- If a tracker's slice of the allocation ring is large, it is taking a bigger
  share of your income — hover a slice for the figure.
- If the ring turns red, you have allocated more than you earn, and the middle
  says by how much.
- If `Remaining` goes negative, the category is overspent.
