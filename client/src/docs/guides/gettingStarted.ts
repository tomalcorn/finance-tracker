import type { Guide } from '@/docs/guide';

export const gettingStarted: Guide = {
  slug: 'getting_started',
  title: 'Getting started',
  order: 1,
  icon: { ios: 'book.fill', web: 'menu_book' },
  body: `
Almost everything starts from the overview on the **Personal** tab: tap a card or a row to
open it.

## Setting up

1. Add your bank accounts under **Bank accounts**, each with what it held when you started
   tracking it.
1. Open **Expenses** under **Budget trackers** and add subcategories for how you want to split
   your spending.
1. Open **Income split**, add your income sources, and set each tracker’s monthly budget.
1. Add your subscriptions.
1. You're ready to start logging payments, on **Payments** or with a Quick
   Expenses button.
1. Use **One-offs** for things you save up for over time or large purchases that don't fit into 
   a regular monthly category, like a holiday or a new laptop.

## Choosing subcategories

- Group similar spending into a few stable subcategories, rather than one for every small
  variation.
- Name them so a review months from now still makes sense.
- If a subcategory’s spending swings a lot from month to month, it probably isn’t regular
  spending. Consider cutting it and giving One-offs more instead.

For the cases where the obvious thing to do is wrong, see
[Common situations](/docs/common_situations).
`,
};
