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

These rows are fixed because they anchor the rest of the model. Expense
categories sit beneath them, income sources point at them, and everything rolls
up into them.

### Expense Categories Tab

Expense categories are the detailed buckets beneath `Expenses`. They are
usually the place where you model spending like groceries, transport, rent, or other regular monthly payments.

A payment only counts toward a category if you attribute it to one, so leaving a
payment uncategorised keeps it out of these totals — see
[getting paid back and moving money between accounts](/payments) for the two
cases where that matters.

You can attribute a payment to a budget tracker directly as well as to one of
its expense categories. Spending booked straight onto `Expenses` still counts
toward that tracker's total; it just isn't broken down any further.

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
`Received Last Month`, and `Share of Income` is worked out against it. Spending
stays on the current month either way. Personal and joint are set separately.

## How The Links Work

Income sources say which budget tracker rows the income contributes toward.
Expense categories work the other way round: each one sits under a budget
tracker — `Expenses`, for the ones this tab creates — and its spending rolls up
into that tracker's `Spent`.

## How To Read The Page

- If `% Spent` is near 100%, that category is close to or at its budget.
- If `Share of Income` is high, that tracker is taking a larger share of your income.
- If `Remaining` goes negative, the category is overspent.
