# finance-tracker

A Streamlit app for tracking personal finances across bank accounts, budget
categories, recurring subscriptions, payments, and one-off savings goals.

The app code lives under `src/`. For a guided walkthrough of each block and
how to use the tracker effectively, see the [markdown docs](./src/docs/01_getting_started.md).

## Data Flow At A Glance

```text
Auth0 login
   |
   v
Streamlit session
   |
   v
Supabase tables and views
   |
   +--> dashboard blocks
   +--> computed metrics
   +--> add/filter dialogs
```

## Database migrations

Versioned SQL schema/view changes live in the [`migrations/`](./migrations/README.md)
package (ops tooling, outside `src/`), applied with `uv run poe migrate`. See the
[migrations README](./migrations/README.md) for the workflow.

## Versioning & releases

Versioning is driven by [Conventional Commits](https://www.conventionalcommits.org/)
at the merge-to-`main` boundary, using [commitizen](https://commitizen-tools.github.io/commitizen/).

- **Pull request titles must be conventional commits** (`type(scope): summary`,
  e.g. `feat(grid): add column filters`; append `!` or a `BREAKING CHANGE:`
  footer for a breaking change). The `PR Title` check enforces this, and because
  PRs are **squash-merged**, the title becomes the single commit on `main`.
- **On merge to `main`**, the `Release` workflow runs commitizen to bump
  `[project].version`, update `CHANGELOG.md`, tag `vX.Y.Z`, and cut a GitHub
  Release. `fix:` bumps the patch, `feat:` the minor, and a breaking change the
  minor while the project is pre-1.0 (`major_version_zero`). Titles like
  `chore:`/`docs:` produce no release.

Preview the next bump locally without writing anything:

```bash
uv run cz bump --dry-run
```
