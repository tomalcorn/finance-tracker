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

## Keeping the deployment awake

Streamlit Community Cloud puts an app to sleep after 12 hours without traffic,
and its traffic counter follows real browser sessions rather than HTTP hits — a
`curl` against a sleeping app returns 200 while the app stays asleep. The
`Keep Awake` workflow therefore visits the app every 6 hours with a headless
browser (`ops/keep_awake.py`), waking it first if it has already dozed off. Six
hours leaves a full window spare, so one delayed run cannot let it sleep.

The visit needs no credentials: an anonymous visitor is redirected straight to
Auth0, and reaching that redirect means the app script ran, which is what resets
the timer. It reads one repository variable (Settings → Secrets and variables →
Actions → Variables):

| Variable | Value |
| --- | --- |
| `STREAMLIT_APP_URL` | The app's Community Cloud URL, e.g. `https://<app>.streamlit.app` |

Run it by hand from the Actions tab, or locally:

```bash
STREAMLIT_APP_URL=https://<app>.streamlit.app uv run python -m ops.keep_awake
```

A failed run uploads a screenshot of whatever the browser was looking at.
GitHub disables scheduled workflows after 60 days without repository activity;
if the app starts sleeping again, check the workflow is still enabled.

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
