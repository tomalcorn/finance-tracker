---
front_matter_title: Subscriptions
slug: subscriptions
order: 6
icon: ":material/autorenew:"
---
# Subscriptions

Subscriptions model recurring payments such as streaming services, software,
insurance, or other repeat charges.

## Key Fields

| Column | Meaning |
| --- | --- |
| `Cmount` | The amount charged each time the subscription runs. |
| `Cadence` | How often the charge happens. |
| `Bank Account ID` | The bank account used to pay for it. |
| `Expense Source ID` | The expense source that should absorb the cost. |
| `Start Date` | When the subscription starts. |
| `End Date` | When the subscription ends, if it is no longer active. |
| `Is Active` | Whether the subscription should still be treated as live. |
| `Monthly Cost` | The monthly equivalent of the recurring charge. |

## Monthly Cost

`Monthly Cost` is computed from the subscription cadence in the view. It turns
weekly, quarterly, yearly, and similar cadences into a monthly equivalent so you
can compare them against your budget on the same scale.

## How To Use It

- Create a subscription when a payment repeats regularly.
- Link it to the right bank account.
- Link it to the right expense source so the spending lands in the right budget.
- Mark it inactive when it no longer applies.

## Important Behaviour

The dashboard runs the subscription reconciler as part of the page flow. That
keeps generated future payments aligned with the subscription records, so the
payments table and the subscription setup do not drift apart.

## Tips

- Keep `Start Date` and `End Date` accurate so future payments are handled
  correctly.
- Use `Expense Source ID` for the category you want the subscription to affect.
- If a service changes frequency, update the cadence instead of creating a second
  subscription row.
