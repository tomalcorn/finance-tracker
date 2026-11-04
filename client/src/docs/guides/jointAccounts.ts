import type { Guide } from '@/docs/guide';

export const jointAccounts: Guide = {
  slug: 'joint_accounts',
  title: 'Joint accounts',
  order: 8,
  icon: { ios: 'person.2.fill', web: 'group' },
  body: `
A joint account lets you and one other person share part of your finances without merging
everything. Shared bills, a shared pot, a holiday you are both saving for: those live in the
joint account. Everything else stays yours alone.

## What is shared and what is not

Everything you already have is private to you. Your partner can’t see your personal spending,
budgets or bank accounts, and you can’t see theirs.

Only what is kept in the joint account is shared. You don’t mark anything as shared yourself:
where you add something decides whether it is private or joint.

Inside a joint account there is no “yours” and “mine”. Both of you can add, change and delete
anything in it, and neither of you has more control than the other.

> **You can only be in one joint account at a time.** If you already share an account with
> someone, you can’t join a second one, for example one with a partner and another with a
> housemate. Worth knowing before you set one up.

## Setting one up

Joint accounts aren’t self-service yet. There is no button to create one or to invite someone,
so it has to be set up by hand behind the scenes.

To get one, ask for a joint account to be created and say who should be on it. Once you are both
added, whatever is kept in the joint account becomes visible to both of you, and its budget
trackers and settings are created for you.

## Where shared data lives

The app has a tab for each half:

- **Personal** is your private accounts, budget and payments, visible only to you.
- **Joint** is the shared account you belong to: its bank accounts, budget, pots, payments and
  subscriptions, visible to both members. Everything on it is in orange, so the two can’t be
  mistaken for each other, and it names the shared account at the top.

Add something on the Joint tab and it is shared; add it on the Personal tab and it stays yours.

## Contributing to the joint account

Money you put into the joint account comes out of your personal money, so the **Contribute**
button is on your **Personal** side: open the Joint tracker under Budget trackers. It only
appears once you are a member of a joint account.

It records the transfer as two payments, an expense on your personal side and a matching income
on the joint side, so both sets of books stay balanced. You choose how much, which personal
account it leaves, which joint account it lands in, and which joint income source it counts
towards, which is what makes it show up in the joint budget’s income. You need a joint bank
account and a joint income source first; the form tells you if either is missing.

Most contributions are standing orders rather than one-offs. For those, use **Joint
contributions** in your personal subscriptions: set the amount, how often and the same choices
once, and the pair of payments is booked for you each time. See the
[Subscriptions guide](/docs/subscriptions) for the details.

If you delete one half of a contribution by hand, delete the other too. Otherwise the money
stays recorded on one side only.

## Seeing each other’s changes

When your partner changes something in the joint account, it appears for you the next time the
screen opens or you come back to the app. If you are expecting a change and can’t see it yet,
leave the screen and open it again.

## What isn’t there yet

Joint accounts are still being built out. At the moment:

- You can’t create one or add someone yourself.
- There is no invite step, so nobody is asked to confirm before being added.
- Everyone on an account has the same rights; there is no owner or admin.
- The Joint tab doesn’t show who else is on the account.
`,
};
