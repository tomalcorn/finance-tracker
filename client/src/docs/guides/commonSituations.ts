import type { Guide } from '@/docs/guide';

export const commonSituations: Guide = {
  slug: 'common_situations',
  title: 'Common situations',
  order: 2,
  icon: { ios: 'lightbulb.fill', web: 'lightbulb' },
  body: `
Some guidance in situations that require a chin scratch.

## Getting paid back

Someone repaying you, like a friend covering half of a dinner or a refunded deposit, can be
recorded two ways. Both are valid; pick by what you want the repayment to be used for.

**Option A: money in, against its own income source.** Create an income source for it and add
a normal payment. It shows up in your income, so you can see it in its own right. Choose this
when the repayment is a genuine inflow you want to track, or when you want to use that money to 
lighten the load across all your expense sources.

**Option B: a negative expense against the original category.** Add money out in the same
category, **but negative** (for example -12.50). This offsets the category
directly, so it reads as though you only ever spent your own share. Choose this for one-off
reimbursements.

A Quick Expenses button can do the same, with a negative amount, if the repayment is always the
same.

## Moving money between your own accounts

Moving your own money is not spending and not income, so it should move both balances without
touching a single budget total. Record it as **two** payments, with the same date and amount:

1. **Money out** on the account it leaves.
2. **Money in** on the account it arrives in.

Leave **both** without a source: no category on the first, no income source on the second. A
payment with no source moves its bank account’s balance and counts for nothing else, which is
exactly what a transfer is.

## A monthly review

1. Open **Payments** and go to the month you want to review.
2. Check each payment has the right category or income source.
3. Compare each bank account’s balance with your banking app, and tick off the final payment
on a day that matches. Tick up to the day *before* today, since you might spend more today.
4. Bank any pots planned for this month.

If an account’s balance doesn’t match, the usual causes are:

- a missing payment
- a payment on the wrong bank account
- a payment dated in the future, which doesn’t count until its date arrives

## Ending a month overspent

Work out how much you overspent by, and add that amount as a new pot on **One-offs**.

Next month, plan as much of it as you can and leave that plan sitting there. You don’t need to
bank it. Just make sure the total planned across your pots still fits your One-offs budget
before you bank anything else. At the end of the month, reduce the pot’s cost by what you had
planned, and carry on until it’s paid off.
`,
};
