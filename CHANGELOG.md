## v1.20.0 (2026-08-20)

### Feat

- measure a pot's share against what is left (#262) (#271)

## v1.19.0 (2026-08-18)

### Feat

- an allocation panel in place of the budget trackers grid (#268)

## v1.18.2 (2026-08-18)

### Fix

- state the totals strip's height so it survives a column (#267)

## v1.18.1 (2026-08-16)

### Refactor

- retire "expense source" from the UI (#252) (#260)

## v1.18.0 (2026-08-16)

### Feat

- offer the whole category tree in the picker (#251) (#259)

## v1.17.0 (2026-08-16)

### Feat

- cut the app over to categories (#250) (#258)

## v1.16.1 (2026-08-15)

### Refactor

- rename expense_source_id to category_id (#257)

## v1.16.0 (2026-08-15)

### Feat

- **db**: add the accrual window that makes a one-off a pot (#256)

## v1.15.0 (2026-08-15)

### Feat

- **db**: compute every category's figures in one view (#255)

## v1.14.0 (2026-08-15)

### Feat

- **db**: add the categories table replacing three aggregates (#253)

## v1.13.4 (2026-08-15)

### Refactor

- **grids**: give each column a label that says what it holds, and a tooltip that explains it (#245)

## v1.13.3 (2026-08-15)

### Refactor

- **grids**: give the budget grids one column order (#244)

## v1.13.2 (2026-08-15)

### Fix

- **grids**: order rows deterministically so deltas map to the right row (#243)

## v1.13.1 (2026-08-13)

### Fix

- **grids**: stop a cleared cell saving null over a non-nullable column (#238)

## v1.13.0 (2026-08-09)

### Feat

- **grids**: total the money columns beneath each grid (#235)

## v1.12.1 (2026-08-07)

### Fix

- **tests**: isolate each integration run on the shared testing database (#234)

## v1.12.0 (2026-08-07)

### Feat

- **quick-expenses**: let the at-the-till form log a negative amount (#233)

## v1.11.0 (2026-08-07)

### Feat

- **payments**: make Income Source optional on income payments (#232)

## v1.10.2 (2026-08-07)

### Fix

- **reconcile**: attribute a re-dated payment to the cycle it settles (#227)

## v1.10.1 (2026-08-01)

### Fix

- **one-offs**: stop the Bank It button vanishing with the display frame (#225)

## v1.10.0 (2026-07-31)

### Feat

- **subscriptions**: recurring joint contributions that book both legs (#223)

## v1.9.0 (2026-07-29)

### Feat

- **settings**: seed a user_settings row on workspace init (#220) (#222)

## v1.8.0 (2026-07-29)

### Feat

- **budget-tracker**: name the income column for the month in force (#218)

## v1.7.0 (2026-07-29)

### Feat

- **settings**: add the Settings page, personal and joint sections (#217)

## v1.6.0 (2026-07-29)

### Feat

- **settings**: add ManageUserSettingsUseCase and its wiring (#216)

## v1.5.0 (2026-07-29)

### Feat

- **settings**: add the user settings entity, read models, and repository (#215)

## v1.4.0 (2026-07-29)

### Feat

- **settings**: add user_settings and window income_sources_view by it (#214)

## v1.3.0 (2026-07-28)

### Feat

- **quick-expenses**: mobile quick-entry page with configurable buttons (#60) (#207)

## v1.2.0 (2026-07-26)

### Feat

- **summary**: add a top-level summary block (#203) (#206)

## v1.1.0 (2026-07-25)

### Feat

- **joint**: associate a joint contribution with a joint income source (#200) (#202)

## v1.0.0 (2026-07-25)

Promotes the joint workflow (#182) to a stable major version. No code changes
since v0.15.0 — this marks the feature set released across v0.6.0–v0.15.0 as
stable, and the point from which breaking changes bump the major version.

### Joint accounts

Two people can each keep private personal finances while sharing a joint ledger:

- **Ownership is a first-class dimension.** Every bank account, budget tracker,
  expense/income source, one-off, payment and subscription is either `personal`
  or `joint`; joint rows carry a `joint_account_id` (#172, #173).
- **Row-level security enforces visibility**, rather than app-side filtering —
  each member sees their own personal rows plus the joint rows of the account
  they belong to (#174).
- **A Joint dashboard** mirrors Personal over the shared account's data (#179).
- **Contribute to Joint** records a transfer as a linked pair — a personal
  expense and a matching joint income — traceable from either side (#178, #180).
- **Joint workspaces seed themselves** with default budget trackers and hidden
  expense sources on first load (#191).

### BREAKING CHANGE

- **The per-user cache invariant is retired** (#176). A read is split into a
  personal slice and an account-scoped joint slice, so one member's joint write
  invalidates exactly the entry their partner reads instead of waiting out a
  TTL. Cache keys changed shape.
- **The repository write contract is replaced** (#198). `BackendUpdates` is gone.
  Every write passes through a frozen entity — built by `build_entities`,
  persisted by `save_entities` — with `apply_edits` / `apply_deletions` carrying
  the grid's editor deltas.
- **Database migrations 0002–0009 must be applied** before this release runs.
  Existing rows default to `ownership_type='personal'`, so personal data is
  untouched by the upgrade.

## v0.15.0 (2026-07-25)

### Feat

- **joint**: joint workflow cutover + entity write gate (#181) (#197)

## v0.14.1 (2026-07-25)

### Refactor

- route every write through a frozen entity gate (#199)

## v0.14.0 (2026-07-23)

### Feat

- **joint**: joint workspace initialisation use case (#191) (#196)

## v0.13.0 (2026-07-22)

### Feat

- **joint**: Contribute button + dialog (#180) (#195)

## v0.12.0 (2026-07-22)

### Feat

- **joint**: joint dashboard page + rename dashboard to personal (#179) (#194)

## v0.11.0 (2026-07-21)

### Feat

- **joint**: contribution use case, personal expense + joint income (#178) (#193)

## v0.10.0 (2026-07-21)

### Feat

- **joint**: split cache keys into personal + joint slices (#176) (#190)

## v0.9.0 (2026-07-21)

### Feat

- **joint**: driven-adapter plumbing for joint accounts + membership (#175) (#189)

## v0.8.0 (2026-07-17)

### Feat

- **rls**: joint-aware RLS policies + ownership constraint (#174) (#187)

## v0.7.1 (2026-07-17)

### Fix

- **payments**: allow expense entry without an expense source (#186) (#188)

## v0.7.0 (2026-07-14)

### Feat

- **migrations**: 0002 joint tables, ownership columns, view review (#185)

## v0.6.0 (2026-07-14)

### Feat

- **migrations**: per-env database URLs + dry-run mode (#184)

## v0.5.0 (2026-07-14)

### Feat

- ownership dimension + joint-account entities/read models (#172) (#183)

## v0.4.0 (2026-07-13)

### Feat

- add versioned SQL migration runner (#171)

## v0.3.0 (2026-07-13)

### Feat

- high-priority backlog UX tweaks (one-offs order, budget sort, income filter) (#170)

## v0.2.4 (2026-07-12)

### Fix

- make cache invalidation cross-session to stop workspace re-init (#160) (#164)

## v0.2.3 (2026-07-12)

### Fix

- link dialog-added expense sources to the expenses tracker (#161) (#163)

## v0.2.2 (2026-07-12)

### Fix

- handle list-valued columns in grid filters (#159) (#162)

## v0.2.1 (2026-07-12)

### Fix

- scope income/expense current_month to current calendar month (#156) (#157)

## v0.2.0 (2026-07-12)

### Feat

- add conventional-commits versioning pipeline (#154)
