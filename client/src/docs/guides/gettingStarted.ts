import type { Guide } from '@/docs/guide';

export const gettingStarted: Guide = {
  slug: 'getting_started',
  title: 'Getting started',
  order: 1,
  icon: { ios: 'book.fill', web: 'menu_book' },
  body: `
This app keeps your personal finances in one place:

- **Budget trackers** show how your money is allocated.
- **Categories** and **income sources** roll up into those trackers.
- **Payments** record the money actually moving in and out.
- **Bank accounts** let you check your payments are up to date.
- **Pots**, under the One-offs tracker, are savings goals that build up over time.
- **Subscriptions** are recurring payments, booked into Payments for you.

The **Personal** and **Joint** tabs each open on an overview of that half of your
finances. Almost everything starts from there: tap a card or a row to open it.

## Signing in

Login is handled through [Auth0](https://auth0.com). The first time you sign in, your
four budget trackers and your settings are created for you.

## Setting up

The usual order is:

1. Add your bank accounts, under **Bank accounts** on the overview.
2. Open **Expenses** under **Budget trackers**, and add subcategories to match how you
   want to split your spending.
3. Open **Income split**, add your income sources, and set each tracker’s monthly budget.
4. Start entering [payments](/docs/payments) and [subscriptions](/docs/subscriptions).
5. Use the One-offs tracker for [savings goals](/docs/one_offs) like holidays, gifts or
   large purchases: anything that isn’t regular monthly spending.

## A good first check

If you’re new to the app, check these three things:

- Do your bank accounts have the right starting balances?
- Do the subcategories match how you want to think about money?
- Does each income source fund the right budget trackers?
`,
};
