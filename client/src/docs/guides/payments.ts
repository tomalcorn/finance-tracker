import type { Guide } from '@/docs/guide';

export const payments: Guide = {
  slug: 'payments',
  title: 'Payments',
  order: 4,
  icon: { ios: 'creditcard.fill', web: 'payments' },
  body: `
Payments are the source of truth for money moving in and out of your accounts. Open them from
the **Payments** card on the overview.

## Finding a payment

The screen shows one month at a time, with what went out and came in. Use the arrows to move
between months.

- **By day** lists each day’s payments, newest first. Each day’s heading shows the net for
  the day and what your accounts held at the end of it.
- **By category** shows money out, largest first. Tap a category to see its payments.
- **All**, **Out** and **In** narrow the list by day.
- **Search** finds payments by what you type. Type **@** to filter by bank account, category,
  income source or name. Filter to one bank account and each day’s heading shows just its balance.

## Adding a payment

Tap **+**, then choose **Money out** or **Money in**.

Money out records money leaving a bank account. It has a name, an amount, a date, a bank
account and optionally a category. It updates your balance and your budget.

Money in records money arriving in a bank account, optionally against an income source. An
entry with no income source still moves the bank account’s balance but rolls up nowhere, which
is what you want for an inflow that isn’t really income.

Tap any payment to edit or delete it. Subscriptions and [contributions](/docs/joint_accounts)
book payments too, and those show up like any other.

## Checking your payments

Each payment has a tick, which you can tap straight from the list. Once you’ve added all your
payments, check your [bank account](/docs/bank_accounts) balances against your banking app,
then tick them off, ideally up to the day *before* today, since you might spend more today.
The overview’s Payments card counts the days still unchecked.

## Getting paid back

Someone repaying you, like a friend covering half of a dinner or a refunded deposit, can be
recorded two ways. Both are valid; pick by what you want the money to mean.

**Option A: money in, against its own income source.** Create an income source for it and add
a normal payment. It shows up in your income, so you can see it in its own right. Choose this
when the repayment is a genuine inflow you want to track, or whenever it arrives in a
*different month* from the original spend.

**Option B: a negative expense against the original category.** Add money out in the same
category, with a minus sign (for example -12.50). This offsets the category directly, so it
reads as though you only ever spent your own share. Choose this for one-off reimbursements.

> **Option B only works within one calendar month.** Monthly totals count the current month’s
> payments only, so a negative dated in a later month reduces *that* month’s total instead,
> overstating the month you spent in and understating the month you were repaid. Across a
> month boundary, use Option A.

You can do this here or on [Quick Expenses](/docs/quick_expenses): type the minus sign at the
till, or give a button a negative amount if the repayment is always the same.

## Moving money between your own accounts

Moving your own money is not spending and not income, so it should move both balances without
touching a single budget total. Record it as **two** payments, with the same date and amount:

1. **Money out** on the account it leaves.
2. **Money in** on the account it arrives in.

Leave **both** without a source: no category on the first, no income source on the second. A
payment with no source moves its bank account’s balance and counts for nothing else, which is
exactly what a transfer is.

## Tips

- Use money out for card payments, transfers that behave like spending, and banked pots.
- Use money in for salary, refunds and other inflows.
- Keep the ticks up to date, so you can tell which payments still need checking.
- Leave a payment’s source blank when it doesn’t belong in your monthly figures. Moving money
  between your own accounts is the usual case. It can take a little getting used to!
`,
};
