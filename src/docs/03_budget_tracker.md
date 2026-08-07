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

## The Three Tabs

### Budget Tracker Tab

This tab shows the fixed tracker rows that act as your main buckets:

- Expenses
- Joint
- One-offs
- Savings

These rows are fixed because they anchor the rest of the model. Expense and
income sources point at them, and other views roll up into them.

### Expense Sources Tab

Expense sources are the detailed buckets beneath the budget tracker. They are
usually the place where you model categories like groceries, transport, rent, or other regular monthly payments.

A payment only counts toward a source if you attribute it to one, so leaving a
payment sourceless keeps it out of these totals — see
[getting paid back and moving money between accounts](/payments) for the two
cases where that matters.

### Income Sources Tab

Income sources are the mirror image for inflows. They show how much income was
received in the roll-up month and which budget tracker rows that income
supports.

Not every inflow belongs here. Money someone owes you back can be recorded as
income against its own source *or* as a negative expense that offsets the
original category — [Payments](/payments) explains when to reach for each.

By default the roll-up month is the current one. If you are paid at the end of
the month, so that each month runs on the previous month's pay, you can move the
income roll-up back a month in [Settings](/settings) — the column then reads
`Previous Month` and the `Split` below is worked out against it. Spending stays
on the current month either way. Personal and joint are set separately.

## Schema

### Budget Tracker Rows

| Column | Meaning |
| --- | --- |
| `Total Budget` | The total amount assigned to that tracker row. |
| `Current Month` | The current-month total rolled up from linked expense sources. |
| `Remaining` | `total_budget - current_month`. |
| `Progress` | The share of the budget already used. |
| `Split` | The share of total income allocated to that tracker row. |

### Expense Sources Rows

| Column | Meaning |
| --- | --- |
| `Budget` | The amount available for that source. |
| `Current Month` | The sum of linked expense payments for the current date window. |
| `Remaining` | `budget - current_month`. |
| `Progress` | The share of the source budget already used. |
| `Split` | The source budget as a share of its linked tracker totals. |

### Income Sources Rows

| Column | Meaning |
| --- | --- |
| `Current Month` / `Previous Month` | The sum of income payments linked to that source, over whichever month the [income roll-up setting](/settings) selects. |
| `Budget Tracker IDs` | The tracker rows that this income supports. |

## How The Links Work

Income sources say which budget tracker rows the income contributes toward. Expense sources work the other way round, except that they all link to the `Expenses` row of `Budget Tracker` and so that link is hidden.

## How To Read The Page

- If `progress` is near 100%, that category is close to or at its budget.
- If `split` is high, that tracker is taking a larger share of your income.
- If `remaining` goes negative, the category is overspent.
