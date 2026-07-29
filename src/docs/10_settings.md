---
front_matter_title: Settings
slug: user_settings
order: 10
icon: ":material/settings:"
---
# Settings

Settings is where you change how the dashboards add things up. Everything here
is a preference, not data — nothing you set on this page creates, edits, or
deletes a payment.

## Personal And Joint Are Separate

The page has one section per half of your finances:

- **Personal** — yours alone.
- **Joint** — the shared account's, shown only if you're a member of one.

They are configured independently, because the two halves rarely work the same
way. The joint settings belong to the *account*, not to you: either member can
change them, and both members see the result. Your personal settings are yours
alone and are never visible to a co-member.

## Income Roll-Up Month

Income sources total up the income payments dated in one month. This chooses
which month that is.

| Setting | What income sources total |
| --- | --- |
| `This month` | Payments dated in the current calendar month. The default. |
| `Last month` | Payments dated in the month before this one. |

Spending is **always** totalled over the current month — this moves only the
income window.

### Why You Might Want Last Month

The budget tracker's `Split` is each tracker row's budget as a share of the
income feeding it. If you're paid at the end of the month, that pay is what the
*next* month is meant to run on, so for most of the month the current-month
income total is £0 and every `Split` reads 0% until the pay lands — then jumps.

Setting the income roll-up month to `Last month` lines the two up: this month's
budget is split against last month's pay, and the figure is stable from the 1st.

### What Changes When You Switch

- The `Current Month` column on the **Income Sources** tab becomes
  `Previous Month`, and totals the earlier window.
- The budget tracker's `Split` is recomputed against that total.
- The income tab says so, so a moved window is never a silent one.

Nothing else moves. Bank balances, payments, expense sources, subscriptions, and
one-offs are all untouched.

## Saving

A change takes effect when you press **Save**, which stays greyed out until
there is something to save. The dashboards pick it up the next time you open
them.
