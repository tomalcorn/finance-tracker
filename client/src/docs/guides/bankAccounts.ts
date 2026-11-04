import type { Guide } from '@/docs/guide';

export const bankAccounts: Guide = {
  slug: 'bank_accounts',
  title: 'Bank accounts',
  order: 5,
  icon: { ios: 'building.columns.fill', web: 'account_balance' },
  body: `
Bank accounts show the live balance of each account you track.

## On the overview

**Bank accounts** on the overview has a tile for each account, with its current balance and a
trend line for the last three months. The heading gives the total across them. A tile’s line
takes about one balance a week, so it shows the general direction rather than every movement.

Use **Add a bank account** under the tiles to add one, with its name and starting balance.

## An account’s page

Tap a tile to open the account:

- **The chart** shows its balance for each day of the last three months, with amounts up the
  side and months along the bottom. Hover over it or drag along it to read any day’s balance.
- **Details** is where you change its name and starting balance.

The starting balance is what was in the account when you started tracking it, below zero if
you owed money on it. The current balance can’t be edited, because it is the starting
balance plus every payment up to today.

An account can only be deleted while no payment or subscription uses it. Deleting one also
removes any quick buttons that log to it.

## How to check an account

1. Start with the starting balance.
2. Enter all known payments.
3. Compare the current balance with your real balance.
4. Tick off the [payments](/docs/payments) you have verified.

If the numbers don’t match, the usual causes are:

- a missing payment
- a payment on the wrong bank account
- a payment dated in the future, which doesn’t count until its date arrives

## Tips

- Keep account names short and obvious, because tiles are narrow.
- Changing a starting balance moves the current balance and the whole trend with it.
`,
};
