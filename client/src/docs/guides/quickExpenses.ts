import type { Guide } from '@/docs/guide';

export const quickExpenses: Guide = {
  slug: 'quick_expenses',
  title: 'Quick Expenses',
  order: 9,
  icon: { ios: 'bolt.fill', web: 'bolt' },
  body: `
Quick Expenses is the first tab, for logging a spend the moment it happens without filling in a
form. Each button is a preset, with a name, an amount, a bank account and a category, and tapping
it logs that payment against today’s date.

The payments it creates are ordinary [payments](/docs/payments). They count towards your budget
and can be edited or deleted like any other.

## Logging a payment

Tap a button. What happens next depends on how it is set up:

- **Log at once** saves the payment immediately, dated today and left unticked so you can check
  it later. A confirmation appears at the bottom of the screen.
- **Ask first** opens a form, already filled in with everything the button knows. Type the part
  that varies, usually the amount, and log it. These buttons say **asks** or **Asks for details**.

The second kind is for spends you repeat at a price that changes, like a weekly shop or a tank of
fuel. You still skip choosing the account and the budget each time.

If you belong to a joint account, a **Personal / Joint** choice appears at the top. It decides
both which buttons you see and which side a tap is logged to.

## Setting up your buttons

Tap **Edit** at the top. While it is on, tapping a button opens its settings instead of logging
anything, and a **New button** tile appears. Tap **Done** when you have finished. You can also
hold any button to edit it at any time.

To remove a button, open it and use **Remove button**. This doesn’t touch the payments it has
already logged.

| Field | What it does |
| --- | --- |
| **Button name** | Required. What the tile says. |
| **Icon** | An optional emoji shown on the tile. |
| **When tapped** | **Log at once** or **Ask first**. |
| **Payment name** | The name the payment is logged under. Defaults to the button name. |
| **Amount** | The expense amount. Negative for money coming back. |
| **Bank account** | The account the money leaves. |
| **Category** | The budget the spend counts against. |
| **Position** | Lower numbers appear first. |

With **Ask first**, the amount and bank account are optional, and anything you leave blank is what
the form asks for at the till. With **Log at once** they are required, because a tap gets no chance
to ask.

The two names are separate on purpose. A “Groceries” button can log “Weekly shop” every time,
without the tile itself ever changing.

## Tips

- Log at once for spends you repeat at the same price, like a coffee or a bus fare. Ask first when
  only the amount moves.
- Give every button a category, so the spend lands in the right budget without a later tidy-up.
- If an amount drifts, edit the button rather than making a second one. Payments already logged keep
  the amount they were logged with.
`,
};
