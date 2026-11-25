import type { Guide } from '@/docs/guide';

export const jointAccounts: Guide = {
  slug: 'joint_accounts',
  title: 'Joint accounts',
  order: 3,
  icon: { ios: 'person.2.fill', web: 'group' },
  body: `
A joint account lets you and one other person share part of your finances without merging
everything. Shared bills, a shared pot, a holiday you are both saving for: those live in the
joint account. Everything else stays yours alone.

## What is shared and what is not

Everything on the **Personal** tab is private to you. Your partner can’t see your personal
spending, budgets or bank accounts, and you can’t see theirs.

Everything on the **Joint** tab is shared. You don’t mark anything as shared yourself: add
something on the Joint tab and it is shared; add it on the Personal tab and it stays yours.

Inside a joint account there is no “yours” and “mine”. Both of you can add, change and delete
anything in it, and neither of you has more control than the other.

> **You can only be in one joint account at a time.** If you already share an account with
> someone, you can’t join a second one, for example one with a partner and another with a
> housemate. Worth knowing before you set one up.

## Setting one up

Joint accounts aren’t self-service yet. There is no button to create one or to invite someone,
so it has to be set up by hand behind the scenes: ask for one, and say who should be on it.
Once you are both added, the Joint tab fills in, and its budget trackers and settings are
created for you.

## Contributing to the joint account

Money you put into the joint account comes out of your personal money, so the **Contribute**
button is on your Personal side: open the Joint tracker under **Budget trackers**.

It records the transfer as two linked payments, an expense on your personal side and a matching
income on the joint side, so both sets of books stay balanced. The joint income source you
choose is what makes it show up in the joint budget’s income. You need a joint bank account and
a joint income source first.

For a standing order, use **Joint contributions** in your personal subscriptions instead, and
the pair of payments is booked for you each time it is due.

If you delete one half of a contribution by hand, delete the other too. Otherwise the money
stays recorded on one side only.

## Seeing each other’s changes

When your partner changes something, it appears for you the next time the screen opens or you
come back to the app. If you are expecting a change and can’t see it yet, leave the screen and
open it again.

## What isn’t there yet

- You can’t create a joint account or add someone yourself.
- There is no invite step, so nobody is asked to confirm before being added.
- Everyone on an account has the same rights; there is no owner or admin.
- The Joint tab doesn’t show who else is on the account.
`,
};
