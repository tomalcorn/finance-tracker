
# ADR: Joint Workflow for Personal + Shared Finances

## Context

We need an approach that lets each user manage personal finances while sharing a joint ledger with another user. Users must only see their personal data and any joint data for shared accounts they belong to. The existing system models Payments, Expense Sources, Income Sources, Budget Tracker entries and Bank Accounts.

## Decision

Introduce a lightweight shared-account model plus an ownership flag on existing financial tables. Use Postgres Row-Level Security (RLS) to enforce visibility rules so the application can query tables normally and rely on the database to return only permitted rows.

## Rationale

- Minimal schema additions and small changes to existing tables
- Keeps auditability: transfers are recorded as an expense (personal) and an income (joint)
- RLS centralizes access control (safer than ad-hoc filtering in the app)
- Simple UX: personal dashboard + joint dashboard

## Schema changes (high level)

1. New tables

- `shared_accounts` — represents a joint/shared account (id, name, created_at)
- `shared_account_members` — links users to `shared_accounts` (shared_account_id, user_id)

1. Small columns on existing tables

- Add `ownership_type` TEXT or ENUM (values: 'personal'|'joint') default 'personal'
- Add `shared_account_id` (nullable FK to `shared_accounts`) — used when `ownership_type = 'joint'`

These apply to: `PAYMENTS`, `EXPENSE_SOURCES`, `INCOME_SOURCES`, `BUDGET_TRACKER`, `BANK_ACCOUNTS`, `FUN_SPENDING`.

Note: Optionally add `linked_payment_id` to `PAYMENTS` to trace transfers (personal -> joint).

## RLS policy summary

For each protected table use the same policy pattern:

```sql
USING / WITH CHECK:

  (ownership_type = 'personal' AND user_id = auth.uid())
  OR
  (ownership_type = 'joint' AND shared_account_id IN (
       SELECT shared_account_id FROM shared_account_members WHERE user_id = auth.uid()
  ))
```

Apply this pattern to: `PAYMENTS`, `EXPENSE_SOURCES`, `INCOME_SOURCES`, `BUDGET_TRACKER`, `BANK_ACCOUNTS`, and `FUN_SPENDING`.

Also enable RLS on `shared_accounts` and `shared_account_members` and create policies so members can see account metadata and membership only if they belong to the account.

## Contribution model recommendation

Treat a user's contribution to joint finances as a personal expense source (e.g., `Joint Contribution`). When a transfer occurs:

- Create a personal expense `PAYMENTS` row (ownership_type='personal', expense_source = 'Joint Contribution')
- Create a joint income `PAYMENTS` row (ownership_type='joint', shared_account_id = <shared id>, income_source = 'Monthly Contributions')

This avoids a dedicated `joint_contributions` table; payments themselves form the canonical history of transfers and are easy to reconcile.

## Frontend / UX

- Personal Dashboard: shows rows where `ownership_type = 'personal'` (RLS will already filter to user's rows)
- Joint Dashboard: shows rows where `ownership_type = 'joint'` for shared accounts the user belongs to
- Provide a flow for creating a contribution: create personal expense payment + matching joint income payment (optionally link them via `linked_payment_id`).

## Migration & setup

1. Create `shared_accounts` and `shared_account_members`.
2. ALTER existing tables to add `ownership_type` and `shared_account_id` (NULL default keeps current rows personal).
3. Enable RLS and create the policies listed above.
4. Create the initial shared account and add member rows.

## Security & operational notes

- Keep `ownership_type` enforced by application UI when creating rows; RLS also enforces checks so writes are constrained to allowed ownership and membership.
- Consider audit triggers or `linked_payment_id` linking for transfer traceability.
- Test RLS thoroughly in a staging environment — mistakes in RLS can leak data.

## Alternatives considered

- Dedicated `joint_contributions` table: captures contribution rules (percentage vs fixed) but adds complexity. Recommendation: start without it and add later if needed.

## Consequences & next steps

- Pros: Minimal schema churn, centralized RLS, simple UX.
- Cons: App must create two payments per contribution (personal expense + joint income) unless an automation is added to do both.

## Next steps

1. Apply DB changes (create `shared_accounts`, `shared_account_members`, ALTER existing tables).
2. Add RLS policies and test with representative user accounts.
3. Update the app flows: contribution UI, joint dashboard, optional `linked_payment_id` support.

## References

- Implementation notes and SQL snippets are available in the original discussion in this file — use them as starting points for migrations and RLS creation.
