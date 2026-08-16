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
- a category
- a payment date
- a `Checked` flag

The `Expense` amount feeds the computed views that update:

- bank account balances
- expense category current-month totals
- budget tracker rollups

## Income Entries

Income entries record money arriving into a bank account. They link together:

- a bank account
- an income source (optional)
- a payment date

The `Income` amount feeds the income source and budget tracker rollups. An entry
left without an income source still moves the bank account balance, but rolls up
nowhere — which is what you want for an inflow that isn't really income, such as
money moved in from another of your own accounts.

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

**Option B — log a negative expense against the original category.**

Add an ordinary expense entry, attribute it to the same `Category` the
original spend came from, and enter the amount with a minus sign (e.g. `-12.50`).
Rather than inventing new income, this offsets that category directly: its
`Spent` falls, `Remaining` rises, and `% Spent` drops, so the category
reads as though you only ever spent your own share. Choose this for one-off
reimbursements of something you already logged as an expense.

One thing to know about Option B: **it only works within one calendar month.**
Expense category rollups count payments from the current month only, so a negative
dated in a later month reduces *that* month's total instead — overstating the
month you spent in and understating the month you were repaid. Across a month
boundary, use Option A.

You can enter it in the payments block or on [Quick Expenses](/quick_expenses) —
type the minus sign at the till, or give a button a negative preset if the repayment is
always the same amount.

### Moving Money Between Your Own Accounts

Moving your own money between two of your accounts is not spending and not
income, so it should move both balances without touching a single budget total.
Record it as **two** entries:

1. An **expense** entry on the account the money leaves.
2. An **income** entry on the account the money arrives in, same date and amount.

Leave **both** entries without a source: no `Category` on the outgoing one,
no `Income Source` on the incoming one. A payment with no source moves its bank
account balance and counts for nothing else, which is exactly what a transfer is.

Attach a category and the transfer would be counted as real spending
against that category; attach an income source and it would be counted as real
income.

## Tips

- Use expense entries for outgoing card payments, transfers that behave like
  spending, and banked one-off contributions.
- Use income entries for salary, refunds, and other inflows.
- Keep the `checked` flag up to date so you can tell which rows still need
  reconciliation.
- In general, leave a payment's source blank when it doesn't belong in your
  monthly figures — no `Category` on something that isn't real spending, no
  `Income Source` on something that isn't real income. Moving money between your
  own accounts is the usual case. This can be a bit tricky to get used to at
  first, but you'll get the hang of it!
