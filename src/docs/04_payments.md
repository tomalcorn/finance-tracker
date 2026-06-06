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

## Tips

- Use expense entries for outgoing card payments, transfers that behave like
  spending, and banked one-off contributions.
- Use income entries for salary, refunds, and other inflows.
- Keep the `checked` flag up to date so you can tell which rows still need
  reconciliation.
- Sometimes you might move money between your listed accounts. When this happens, do not assign an `Expense Source` to that payment. In general, do not assign an `Expense Source` to a payment that doesn't contribute to your monthly outgoings. This can be a bit tricky to get used to at first, but you'll get the hang of it!
