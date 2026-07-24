
# ADR: Joint Workflow for Personal + Shared Finances

> **⚠️ Superseded — historical record only.** This ADR is the original sketch of
> the joint workflow. It has been implemented and superseded by the **Joint
> Workflow epic (#182)**, which reconciled it with the codebase as it stands
> after the hexagonal refactor (#102), the migration runner (#158/#171), and the
> cross-session cache (#164). Do not treat the SQL and flows below as current —
> take the epic and the `.claude/CLAUDE.md` invariants (Cache / Read strategy /
> architecture) as the source of truth. The main corrections the epic made:
>
> - **RLS keys on `public.user_id()` (the Auth0 `userId` TEXT claim), not
>   `auth.uid()`.** The app authenticates via a minted Supabase JWT and
>   `joint_account_members.user_id` is a TEXT Auth0 sub, not a UUID — so every
>   `auth.uid()` snippet below is wrong for this app.
> - **Schema ships as versioned migrations** (`migrations/versions/0002_joint_workflow.sql`
>   onward), and **RLS is a versioned prod-only overlay**
>   (`migrations/versions/prod/0005_enable_rls.sql`), applied by the migration
>   runner — not hand-applied SQL.
> - **The "backend RPC / server endpoint" is a `use_cases/` use case here.**
>   There is no server tier; cross-aggregate coordination (create joint account,
>   contribute) lives in use cases, plain CRUD goes through the grid port.
> - **Contributions reuse existing anchors** (`BudgetTrackerName.JOINT` + a
>   hidden "Joint" expense source seeded by workspace init) rather than a
>   dedicated `joint_contributions` table.
> - **The cache invariant changed** (#176): reads are split into a personal
>   slice and an account-scoped joint slice so a partner's joint write
>   invalidates the entry the other member reads.

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

- `joint_accounts` — represents a joint/shared account (id, name, created_at)
- `joint_account_members` — links users to `joint_accounts` (joint_account_id, user_id)

1. Small columns on existing tables

- Add `ownership_type` TEXT or ENUM (values: 'personal'|'joint') default 'personal'
- Add `joint_account_id` (nullable FK to `joint_accounts`) — used when `ownership_type = 'joint'`

These apply to: `PAYMENTS`, `EXPENSE_SOURCES`, `INCOME_SOURCES`, `BUDGET_TRACKER`, `BANK_ACCOUNTS`, `ONE_OFFS`.

Note: Optionally add `linked_payment_id` to `PAYMENTS` to trace transfers (personal -> joint).

## RLS policy summary

For each protected table use the same policy pattern:

```sql
USING / WITH CHECK:

    (ownership_type = 'personal' AND user_id = auth.uid())
    OR
    (ownership_type = 'joint' AND joint_account_id IN (
      SELECT joint_account_id FROM joint_account_members WHERE user_id = auth.uid()
    ))
```

Apply this pattern to: `PAYMENTS`, `EXPENSE_SOURCES`, `INCOME_SOURCES`, `BUDGET_TRACKER`, `BANK_ACCOUNTS`, and `ONE_OFFS`.

Also enable RLS on `joint_accounts` and `joint_account_members` and create policies so members can see account metadata and membership only if they belong to the account.

## Contribution model recommendation

Treat a user's contribution to joint finances as a personal expense source (e.g., `Joint Contribution`). When a transfer occurs:

- Create a personal expense `PAYMENTS` row (ownership_type='personal', expense_source = 'Joint Contribution')
- Create a joint income `PAYMENTS` row (ownership_type='joint', joint_account_id = <joint id>, income_source = 'Monthly Contributions')

This avoids a dedicated `joint_contributions` table; payments themselves form the canonical history of transfers and are easy to reconcile.

## Frontend / UX

- Personal Dashboard: shows rows where `ownership_type = 'personal'` (RLS will already filter to user's rows)
- Joint Dashboard: shows rows where `ownership_type = 'joint'` for shared accounts the user belongs to
- Provide a flow for creating a contribution: create personal expense payment + matching joint income payment (optionally link them via `linked_payment_id`).

## Migration & setup

1. Create `joint_accounts` and `joint_account_members`.
2. ALTER existing tables to add `ownership_type` and `joint_account_id` (NULL default keeps current rows personal).
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

1. Apply DB changes (create `joint_accounts`, `joint_account_members`, ALTER existing tables).
2. Add RLS policies and test with representative user accounts.
3. Update the app flows: contribution UI, joint dashboard, optional `linked_payment_id` support.

## Example Scenarios

### Adding a new personal bank account

- **UI:** User opens "Add bank account", fills name/account fields. This is a personal account so `ownership_type` is `personal` by default.
- **Frontend code:** Validate fields, then insert to `BANK_ACCOUNTS` with `user_id = auth.uid()`, `ownership_type = 'personal'` and `joint_account_id = NULL`.
- **Backend / DB:** Example insert:

```sql
INSERT INTO BANK_ACCOUNTS (user_id, name, account_number, ownership_type, joint_account_id)
VALUES (auth.uid(), 'My Checking', 'xxxx', 'personal', NULL);
```

RLS will allow the insert if the `WITH CHECK` condition for personal rows is satisfied (i.e., `user_id = auth.uid()`).

### Creating a new joint bank account (create account + assign creator)

- **UI:** User opens "Create joint account", enters the joint account name and bank details. This flow creates the joint account and assigns the creator as an initial member.
- **Frontend code:** Call a backend endpoint that runs a transaction to create the joint account, add the creator to `joint_account_members`, and insert the `BANK_ACCOUNTS` row with `ownership_type = 'joint'` and `joint_account_id` set to the newly created account.
- **Backend / DB:** Example transactional sequence (pseudocode):

```sql
BEGIN;
INSERT INTO joint_accounts (name) VALUES ('Our Joint Account') RETURNING id INTO new_joint_id;
INSERT INTO joint_account_members (joint_account_id, user_id) VALUES (new_joint_id, auth.uid());
INSERT INTO BANK_ACCOUNTS (user_id, name, account_number, ownership_type, joint_account_id)
VALUES (auth.uid(), 'Joint Checking', 'xxxx', 'joint', new_joint_id);
COMMIT;
```

RLS considerations: the transaction must satisfy `WITH CHECK` for each insert. Creating the joint account and its initial membership is a common pattern — implement as a single backend RPC or server endpoint (trusted role) if RLS rules prevent straightforward client-side inserts.

These two scenarios contrast the simple personal-account creation (no joint state) with the joint-account creation flow that establishes the joint entity and membership atomically.

### Short-term (no-code) — add a user directly via backend/DB

- When you need a quick, no-code solution you can add a member directly in the DB (e.g., using Supabase SQL editor, psql, or your DB admin panel).
- Steps:
  1. Resolve the target `user_id` (look up by email in the `users` table) and the `joint_account_id`.
  2. Run an insert as a DB admin:

```sql
INSERT INTO joint_account_members (joint_account_id, user_id)
VALUES ('<joint-account-id>', '<new-user-id>');
```

  1. Verify the insert succeeded (check unique constraint) and that the app shows the new member on the joint-account page.

- Notes:
  - This bypasses any invite UX and requires you to be a database admin or use an admin SQL panel. It also bypasses any email/accept flow and should be used sparingly.
  - If you want the user to confirm, insert into an `invites` table instead and have the app consume the invite when the user accepts.
  - Ensure you follow the same role semantics you plan to implement later (owner/admin/member) so app behavior stays predictable.

## References

- Implementation notes and SQL snippets are available in the original discussion in this file — use them as starting points for migrations and RLS creation.
