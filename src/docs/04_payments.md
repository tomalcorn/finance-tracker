---
front_matter_title: Payments
slug: payments
order: 4
icon: ":material/payments:"
---
# Payments

Payments are the source of truth for money moving in and out of your accounts.
There are two entry types:

- expense entries
- income entries

## Expense Entries

Expense entries record money leaving a bank account. They link together:

- a bank account
- an expense source
- a payment date
- a `Checked` flag

The `Expense` amount feeds the computed views that update:

- bank account balances
- expense source current-month totals
- budget tracker rollups

## Income Entries

Income entries record money arriving into a bank account. They link together:

- a bank account
- an income source
- a payment date

The `Income` amount feeds the income source and budget tracker rollups.

## Practical Workflow

1. Click the :material/plus: button to add a new payment.
2. Make sure the bank account is correct.
3. Link the right expense or income source.
4. Once you have gone through and added all your payments, check that the relevant Bank Account balances match what you see in your bank account app. Then tick `Checked`, ideally for the date *before* today (since you might spend more today!).

## Common Scenarios

### Getting Paid Back

Someone repaying you — a friend covering their half of a dinner, a refunded
deposit — can be recorded two ways. Both are valid; pick by what you want the
money to *mean* in your reports.

**Option A — log it as income against its own income source.**

Create an income source for the repayment and add a normal income entry against
it. The inflow shows up in the income source and budget tracker rollups, so you
can see and report on it in its own right. Choose this when the repayment is a
genuine inflow you want to track — or whenever it arrives in a *different month*
from the original spend (see the caveat below).

**Option B — log a negative expense against the original expense source.**

Add an ordinary expense entry, attribute it to the same `Expense Source` the
original spend came from, and enter the amount with a minus sign (e.g. `-12.50`).
Rather than inventing new income, this offsets that category directly: its
`Current Month` falls, `Remaining` rises, and `Progress` drops, so the category
reads as though you only ever spent your own share. Choose this for one-off
reimbursements of something you already logged as an expense.

Two things to know about Option B:

- **It only works within one calendar month.** Expense source rollups count
  payments from the current month only, so a negative dated in a later month
  reduces *that* month's total instead — overstating the month you spent in and
  understating the month you were repaid. Across a month boundary, use Option A.
- **Enter it on this page.** [Quick Expenses](/quick_expenses) will not accept a
  negative amount.

### Moving Money Between Your Own Accounts

Moving your own money between two of your accounts is not spending and not
income, so it should move both balances without touching a single budget total.
Record it as **two** entries:

1. An **expense** entry on the account the money leaves.
2. An **income** entry on the account the money arrives in, same date and amount.

Leave **both** without a source — no `Expense Source`, no `Income Source`.

This works because bank account balances are worked out per account from the
payments on it, and never look at sources at all. Both balances move by the
right amount, while the transfer stays out of every expense source and budget
tracker rollup. Attach an expense source and the transfer would be counted as
real spending against that category.

## Tips

- Use expense entries for outgoing card payments, transfers that behave like
  spending, and banked one-off contributions.
- Use income entries for salary, refunds, and other inflows.
- Keep the `checked` flag up to date so you can tell which rows still need
  reconciliation.
- In general, do not assign an `Expense Source` to a payment that doesn't
  contribute to your monthly outgoings — moving money between your own accounts
  being the usual case. This can be a bit tricky to get used to at first, but
  you'll get the hang of it!
