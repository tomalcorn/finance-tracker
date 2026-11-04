import type { Guide } from '@/docs/guide';

export const subscriptions: Guide = {
  slug: 'subscriptions',
  title: 'Subscriptions',
  order: 6,
  icon: { ios: 'arrow.triangle.2.circlepath', web: 'autorenew' },
  body: `
Subscriptions are recurring payments such as streaming services, software or insurance. Open
them from the **Subscriptions** card on the overview.

The screen shows what they cost a month and a year, then each one that is running, most
expensive first. Anything ended or switched off is listed under **Not running**.

## Adding one

| Field | What it means |
| --- | --- |
| **Amount** | What is charged each time it runs. |
| **How often** | Weekly, monthly, quarterly, biannually or yearly. |
| **Bank account** | The account that pays for it. |
| **Category** | The budget tracker or subcategory it counts against. |
| **Starts** | When it starts. |
| **Ends** | When it ends, if it does. |
| **Active** | Turn off to stop it booking payments. |

Its monthly cost is worked out for you, so a yearly charge can be compared with your budget on
the same scale.

## How payments get booked

The app books what is due when it opens, and again whenever you change a subscription, so
you don’t enter these payments yourself. Each one shows up in [Payments](/docs/payments) like any other.

Switch one off or give it an end date, and any payments still to come are removed. Payments
already in the past are left alone.

## Joint contributions

If you belong to a joint account, the Personal half’s subscriptions have a second view: **Joint
contributions**. Each one is a standing order into the joint account: the same transfer as the
[Contribute button](/docs/joint_accounts), repeating on a schedule.

| Field | What it means |
| --- | --- |
| **From (personal)** | The personal bank account the money leaves. |
| **To (joint)** | The joint bank account it arrives in. |
| **Joint income source** | What it counts towards in the joint budget. |

Each time one falls due it books **two** payments: an expense on your personal side and a
matching income on the joint side, linked to each other. Switch it off or give it an end date,
and any future pair is removed from both sets of books together.

You don’t pick a category. The personal side is always booked against your Joint budget
tracker, so all your contributions land in one place in your own budget.

## Tips

- Keep the start and end dates accurate, so future payments are handled correctly.
- If a service changes how often it charges, edit it rather than adding a second one.
`,
};
