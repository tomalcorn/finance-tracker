---
front_matter_title: Quick Expenses
slug: quick_expenses
order: 9
icon: ":material/bolt:"
---
# Quick Expenses

Quick Expenses is the page for logging a spend the moment it happens, from a
phone, without filling in a form. Each button is a preset — a name, an amount, a
bank account, and an expense source — and tapping it logs that payment against
today's date.

The payments it creates are ordinary payments. They show up on the dashboard,
count towards your budget, and can be edited or deleted there like any other.

## Logging A Payment

Tap a button. What happens next depends on how that button is set up:

- **Log straight away** — the payment is saved immediately, dated today and left
  unchecked so you can tick it off later when you reconcile the account. A
  confirmation appears at the bottom of the screen.
- **Ask first** — a form opens, already filled in with everything the button
  knows. Type the part that varies, usually the amount, and log it. These
  buttons end in `…` so you can tell them apart at a glance.

The second kind is for the spends you repeat at a price that changes — a weekly
shop, a tank of fuel. You still skip choosing the account and the budget every
time; you only fill in what actually differs.

If you belong to a joint account, a **Personal / Joint** selector appears at the
top of the page. It decides both which buttons you see and which side of your
finances a tap is logged to, so a shared coffee run can go straight into the
joint ledger.

## Setting Up Your Buttons

Turn on **Edit buttons** at the top of the page. While it is on, tapping a
button no longer logs anything — it opens that button's settings instead.

- **Add** — tap **+** and fill in the details.
- **Change** — tap the button you want to change; its current settings are
  already filled in.
- **Remove** — tap **−** to turn on remove mode, then tap the button you want
  gone and confirm. Removing a button does not touch the payments it has
  already logged.

The form comes in two halves. The top half is the button itself:

| Field | What it does |
| --- | --- |
| Button name | Required. What the tile says — the thing you tap. |
| Icon | An optional emoji shown before the name. |
| Position | Lower numbers appear first in the grid. |
| Ask for details when tapped | Off: a tap logs the payment immediately. On: a tap opens a form pre-filled with the half below. |

Below the divider is the payment it creates:

| Field | What it does |
| --- | --- |
| Payment name | The name the payment is logged under. Defaults to the button name. |
| Amount | The expense amount. |
| Bank account | The account the money leaves. |
| Expense source | The budget the spend counts against. |

With **Ask for details** turned on, that whole lower half is optional —
anything you leave blank is simply what the form asks for at the till. With it
off, the amount and the bank account are required, because a tap gets no chance
to ask.

The two names are separate on purpose. A "Groceries" button can log "Weekly
shop" every time, or leave the payment name to be typed in at the till, without
the tile itself ever changing.

Turn **Edit buttons** back off when you are done, and the page returns to
one-tap logging.

## Tips

- Log straight away for the spends you repeat at the same price — a coffee, a
  bus fare, a regular lunch. Ask first when only the amount moves.
- Give every button an expense source, so the spend lands in the right budget
  without a later tidy-up.
- If an amount drifts, edit the button rather than making a second one — the
  payments already logged keep the amount they were logged with.
