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
