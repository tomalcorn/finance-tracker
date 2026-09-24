# Architecture Decision Records

Significant, hard-to-reverse decisions about how the app is built are recorded
here as ADRs, one numbered markdown file per decision. Each starts life as an
`[ADR]` issue (see `.github/ISSUE_TEMPLATE/adr.md`) and is merged through a PR.

An ADR is never rewritten once accepted. If a decision changes, add a new ADR
that supersedes it and set the old one's status to `Superseded by NNNN`.

| ADR | Title | Status |
| --- | --- | --- |
| [0001](./0001-mobile-via-progressive-web-app.md) | Deliver mobile as an installable web app (PWA) from one TypeScript codebase | Proposed |

## Template

```markdown
# NNNN. Title

- **Status:** Proposed | Accepted | Superseded by NNNN
- **Date:** YYYY-MM-DD
- **Issue:** #NNN

## Context
## Decision
## Options considered
## Consequences
## Plan
```
