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

### Income Sources Tab

Income sources are the mirror image for inflows. They show how much income was
received this month and which budget tracker rows that income supports.

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
| `Current Month` | The sum of income payments linked to that source. |
| `Budget Tracker IDs` | The tracker rows that this income supports. |

## How The Links Work

Income sources say which budget tracker rows the income contributes toward. Expense sources work the other way round, except that they all link to the `Expenses` row of `Budget Tracker` and so that link is hidden.

## How To Read The Page

- If `progress` is near 100%, that category is close to or at its budget.
- If `split` is high, that tracker is taking a larger share of your income.
- If `remaining` goes negative, the category is overspent.
