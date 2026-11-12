import type { Guide } from '@/docs/guide';

export const oneOffs: Guide = {
  slug: 'one_offs',
  title: 'One-offs',
  order: 2,
  icon: { ios: 'circle.hexagongrid.fill', web: 'bubble_chart' },
  body: `
One-offs are things you want to save up for over time, outside your normal monthly
spending. Each one is a **pot** under the One-offs [budget tracker](/docs/budget_tracker).
Examples include:

- holidays
- a new laptop
- car repairs
- gifts
- overspend from a previous month (use with caution!)

## How to use them

- Add a pot when a savings goal starts, with **Add a pot** on the One-offs tracker.
- Set **Planned this month** when you want to earmark money for it.
- Use **Bank it** to pay the planned amount into the pot. The recommended approach is to
  move the money into a separate easy-access savings account at the same time.
- When you come to buy the thing, move the money from savings into your current account.
- Open a pot to change its target or its plan.
- Delete a pot if you no longer need it. Any payments banked into it are kept and move up
  to the One-offs tracker, so deleting a pot never deletes spending history.

## Banking pots

**Bank it** turns the planned amounts into real payments. You choose which pots and
the account the money leaves, and it books one expense per pot, named after it.

What a pot has **saved** is its **Already saved** figure plus every payment booked to it,
so it rises by what you just banked. **Planned this month** stays where you set it: it is
the monthly allowance for the pot, and nothing reduces it.

That makes the money part of your actual spending history, not just a paper allocation.
Make sure you actually move the money into your savings before you use **Bank it**.

## Practical tips

- Keep **Cost** as the full target, not the amount left.
- Use **Planned this month** for the money you are assigning right now.
- Treat **Saved** as the money already protected for the goal.
- If a pot’s saved figure stays flat for too long, you may need to reduce the target or
  change the monthly plan.
- Check the total planned against your One-offs budget before you bank, while the month’s
  allowance is still unspent. The One-offs tracker shows the total planned and how much of
  the budget it leaves.
- The lighter end of a pot’s bar is this month’s plan, and the line under it says what will
  be left to go once the plan is banked.

## Overspend from a previous month

If you end the month in the red, work out how much you overspent by.

Add that amount as a new pot. Next month, plan as much of it as you can and leave that
plan sitting there. You don’t need to bank it. Just make sure the total planned across
your pots still fits your One-offs budget before you bank anything else. At the end of the
month, reduce the pot’s cost by what you had planned, and carry on until it’s paid off.
`,
};
