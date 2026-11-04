import type { Guide } from '@/docs/guide';

export const financeAnalysis: Guide = {
  slug: 'finance_analysis',
  title: 'Finance analysis',
  order: 7,
  icon: { ios: 'chart.bar.fill', web: 'insights' },
  body: `
This app is most useful as a way of making decisions, not just entering data. The core question
is always: am I on track?

## The summary

The top of each overview gives you the answer at a glance:

- **Total balance** is what all your accounts hold, with a line over the last six month-ends.
- **Remaining budget** is what is left of your trackers' budgets this month, and its share of
  the total.
- **Spent this month** is your expenses so far, how that compares with last month, and bars
  for the last six months. Red means more than last month; green means less.

## Reading the budget

Look at the budget next when you review your finances.

- A tracker’s bar shows how much of its budget has gone, and the same goes for a subcategory.
- What is **left** tells you what you can still spend.
- The ring on **Income split** shows how each tracker’s budget compares with your income.

If a tracker’s bar is climbing quickly and its slice of the ring is already large, it may be
taking a bigger share of your income than you intended.

## Tracking pots

[Pots](/docs/one_offs) are easiest to judge as a trend:

- If **Saved** is rising steadily, the goal is healthy.
- If **Planned** is set month after month with nothing banked, the goal is being planned
  for but never paid into.
- If **To go** isn’t falling, the target may be too ambitious for now.

## A monthly review

1. Open [Payments](/docs/payments) and go to the month you want to review.
2. Check that your payments have the right categories and income sources.
3. Tick them off once they match your statement.
4. Compare your [bank account](/docs/bank_accounts) tiles with your real balances.
5. Review any pots that should be banked this month.

## Categorising well

Good categories make the rest of the app much more useful.

- Group similar spending into stable subcategories.
- Avoid a new one for every small variation.
- Keep names descriptive enough that future reviews make sense.
- If a subcategory’s spending varies a lot from month to month, it may not be a very good
  one. Expenses are there for regular monthly spending. Consider cutting it and allocating
  more to One-offs instead.

## What to watch for

- repeated overspending in the same category
- a tracker that is always too tight
- a bank account balance that your payments can’t explain
`,
};
