# finance-tracker — architecture & conventions

A Streamlit app for tracking personal finances (bank accounts, budget
categories, subscriptions, payments, one-off savings goals). Data lives in
Supabase; auth is Auth0 via a minted Supabase JWT.

## Commands

- `uv run poe app` — run the Streamlit app
- `uv run poe lint` — `ruff check` + `ty check`
- `uv run ruff format` — format
- `uv run pytest` — tests (needs `.streamlit/secrets.toml`; CI injects it)

## Architecture (hexagonal)

Dependencies point inward. The domain and use cases know nothing about
Streamlit or Supabase.

```
driving_adapters (UI)  ─┐
                        ├─► composition ──► use_cases ──► ports ◄── driven_adapters
domain (entities, read_models, errors) is depended on by everything inward
```

- **`domain/`** — `entities` (write models), `read_models` (frozen view
  models carrying SQL-view computed columns), `errors`, `query`. Pure pydantic;
  no framework imports.
- **`ports/`** — abstract interfaces the app needs from persistence. One
  generic `Repository[EntityT]` (`get_all` / `get_by_ids` / `save` / `apply`).
- **`use_cases/`** — application logic (reconcile subscriptions, bank one-offs,
  initialise workspace). Depend on ports, injected via constructors.
- **`driven_adapters/`** — Supabase implementation. One generic
  `SupabaseRepository[EntityT, ViewT]` configured per aggregate by a `RepoSpec`
  (parser, view model, read/write tables); typed factory functions build each.
  `driven_adapters/cache.py` defines the `CacheGateway` port the repositories
  depend on — the driven side declares what it needs from a cache, but does not
  know Streamlit.
- **`driving_adapters/`** — the Streamlit UI: `blocks`, `components` (grid +
  buttons), `pages`. Owns the `GridDataSource` port a grid needs, and the
  `cache` implementation (`@st.cache_data` + per-table version counters).
- **`composition/`** — the only layer that sees both sides. Builds the cache,
  wires it into repositories, and hands repositories/use-cases to the UI.
  `dashboard.py` is the composition root for the page.

### Key seams

- **Cache**: the implementation is UI-owned (Streamlit specifics) and offered
  *up* to composition, which injects it into repositories as a `CacheGateway`.
  The UI must not import the driven adapter and the driven adapter must not
  import Streamlit. The cache is global across sessions and keyed by table, so
  repositories re-scope reads to the current `user_id` in Python.
- **Grid**: `SupabaseRepository` satisfies the UI-owned `GridDataSource` port
  directly (`rows` / `unique_values` / `apply`) — no adapter in between.
- **Payments**: the only aggregate with no SQL view and a discriminated-union
  row shape (expense vs income), parsed via a `TypeAdapter` supplied to its
  `RepoSpec`.

## Conventions

- **Keep prose out of the code.** Docstrings say what a thing is and how to use
  it — not the history or rationale of a decision. Architecture/decision context
  belongs here in `CLAUDE.md` (or the relevant GitHub issue), not in module
  headers.
- **No banner/section-divider comments** (`# ----- Foo -----`) in `src/`. Let
  structure and names carry the file. Banners are tolerable in tests/fixtures.
- Prefer typed dicts (`dict[str, object]`) over bare `dict`.
- Errors crossing the adapter boundary are translated to `AdapterError` so use
  cases never see Supabase/cache internals.
