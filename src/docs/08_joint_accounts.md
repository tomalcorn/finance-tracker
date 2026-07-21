---
front_matter_title: Joint Accounts
slug: joint_accounts
order: 8
icon: ":material/group:"
---
# Joint Accounts

A joint account lets two people share part of their finances without merging
everything. Your personal records stay yours; only the records marked as joint
are shared with the other member.

## How Ownership Works

Every record — bank accounts, budget trackers, expense and income sources,
payments, one-offs, subscriptions — carries an ownership marker.

| Ownership | Who can see and edit it |
| --- | --- |
| `personal` | Only you. This is the default for everything. |
| `joint` | Every member of the joint account it belongs to. |

Joint records are **fully shared**: any member can read, edit, and delete any
joint record on the account. There is no per-member restriction within a joint
account, and no owner/admin distinction.

Records you already have are personal. Nothing becomes shared unless it is
explicitly created as joint.

## What A Joint Account Is Made Of

- A joint account row, holding the account's name.
- One membership row per person on the account.

A user belongs to **at most one joint account**. Adding a second membership for
the same person is rejected by the database rather than silently ignored.

## Setting One Up

There is no joint account screen in the app yet. Setting one up is a manual
database step performed by an administrator:

1. Create the joint account row.
2. Add a membership row for each person, using their Auth0 user ID.

Once both membership rows exist, each member's joint records become visible to
the other.

## Seeing Each Other's Changes

Joint data is cached per joint account rather than per user. When one member
saves a joint record, the shared cache entry is cleared for everyone on the
account, so the other member sees the change on their next load instead of
waiting for the cache to expire.

## Current Limitations

- No in-app flow for creating a joint account or adding a member — both are
  manual database steps today.
- No invite or accept step. A member is added directly; the person is not asked
  to confirm.
- No member roles. Everyone on an account has the same rights over its joint
  records.
- No screen for viewing or entering joint records yet, so the shared data has no
  UI of its own at the moment.

Building the in-app version of this — a create-account flow and an invite or
add-member step — is possible, and can be picked up if there is enough demand
for it.
