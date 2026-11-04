import type { Guide } from '@/docs/guide';

export const budgetTracker: Guide = {
  slug: 'budget_tracker',
  title: 'Budget tracker',
  order: 3,
  icon: { ios: 'chart.pie.fill', web: 'pie_chart' },
  body: `
The budget is the top level of the app. It answers:

- how much budget each tracker has
- how much of that has been used this month
- how much is left
- how it compares with your income

## The trackers

There are four fixed budget trackers, which act as your main buckets:

- Expenses
- Joint
- One-offs
- Savings

They are fixed because they anchor everything else: subcategories sit beneath them, income
sources point at them, and everything rolls up into them. They appear under **Budget
trackers** on the overview, each with what it has left. Tap one to open it.

A joint account has every tracker except Joint, because that one is the personal side of
[contributing to a joint account](/docs/joint_accounts).

## Income split

The **Income split** card on the overview opens the place to see your whole month at once:

- a ring of your income, split between the trackers, with what is left unallocated in
  grey and its figure in the middle
- each tracker’s monthly budget, which you can edit and save together with **Save budgets**
- your income sources

Allocate more than you earn and the ring is outlined in red, and the middle says by how much.

## One tracker at a time

Opening a tracker shows its budget, what has been spent and what is left, then the
subcategories beneath it. **Change budget** sets that tracker’s budget on its own.

Expenses is usually where you model spending like groceries, transport or rent. One-offs
holds [pots](/docs/one_offs), which behave differently enough to have their own guide. Joint
and Savings are each a single pot of money, so neither is broken down.

A payment only counts toward a category if you attribute it to one, so leaving a payment
without a category keeps it out of these totals. [Payments](/docs/payments) covers the two
cases where that matters: getting paid back, and moving money between your own accounts.

You can attribute a payment to a tracker directly as well as to one of its subcategories.
Spending booked straight onto Expenses still counts toward that tracker’s total; it just
isn’t broken down any further.

## Income sources

Income sources are the mirror image for money coming in. Each shows how much was received
in the month and which trackers that income funds. Tap one to see the payments behind it.

Not every inflow belongs here. Money someone owes you can be recorded as income against its
own source, or as a negative expense that offsets the original category. [Payments](/docs/payments)
explains when to use each.

By default your income is counted over the current month. If you are paid at the end of the
month, so each month runs on the previous month’s pay, set **Income month** to **Last month**
in [Settings](/settings). The income split is then measured against last month’s income, while
spending stays on the current month. Personal and joint are set separately.

## How to read it

- If a tracker’s bar is nearly full, it is close to its budget. The same goes for a
  subcategory.
- If a tracker’s slice of the ring is large, it is taking a bigger share of your income.
- If the ring is outlined in red, you have allocated more than you earn.
- If a tracker shows **Over budget**, it has been overspent.
`,
};
