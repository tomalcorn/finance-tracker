# finance-tracker

This app helps manage your personal finances!

## DFE workflow

For the first pass:

```mermaid
---
title: First Pass
---
flowchart TD
    n2["DFEHandler"] --> n7["DFEHandler.config"] & n10["sorts"]
    n6["st.data_editor"] -. on_edits .-> n8["working_df"]
    n5["current_df"] --> n6
    n7 --> n6
    n4["table name + key"] --> n9["init (@cache)"]
    n3["dfh.Config"] --> n9
    n1["supabase"] --> n9
    n9 --> n2
    n10 --> n5
    n7@{ shape: out-in}
    n8@{ shape: out-in}
    n5@{ shape: out-in}
    n4@{ shape: in-out}
    n3@{ shape: in-out}
    n1@{ shape: db}
     n2:::Aqua
     n2:::Sky
     n7:::Pine
     n10:::Peach
     n6:::Sky
     n8:::Pine
     n5:::Pine
     n9:::Peach
    classDef Aqua stroke-width:1px, stroke-dasharray:none, stroke:#46EDC8, fill:#DEFFF8, color:#378E7A
    classDef Sky stroke-width:1px, stroke-dasharray:none, stroke:#374D7C, fill:#E2EBFF, color:#374D7C
    classDef Pine stroke-width:1px, stroke-dasharray:none, stroke:#254336, fill:#27654A, color:#FFFFFF
    classDef Peach stroke-width:1px, stroke-dasharray:none, stroke:#FBB35A, fill:#FFEFDB, color:#8F632D


```

For future passes:

```mermaid
---
title: Future Passes
---
flowchart TD
    n2["DFEHandler"] -- 3 --> n7["DFEHandler.config"]
    n2 -- 2 --> n11["sort"]
    n2 -- "1- with working and current df" --> n10["sync"]
    n6["st.data_editor"] -. on_edits .-> n8["working_df"]
    n5["current_df"] --> n6
    n7 --> n6
    n9["working_df"] --> n2
    n10 --> n1["supabase"]
    n8 --> n2
    n11 --> n5
    n12["current_df"] --> n2
    n7@{ shape: out-in}
    n8@{ shape: out-in}
    n5@{ shape: out-in}
    n9@{ shape: in-out}
    n1@{ shape: db}
    n12@{ shape: in-out}
     n2:::Aqua
     n2:::Sky
     n7:::Pine
     n11:::Peach
     n10:::Peach
     n6:::Sky
     n8:::Pine
     n5:::Pine
     n9:::Pine
     n12:::Pine
    classDef Aqua stroke-width:1px, stroke-dasharray:none, stroke:#46EDC8, fill:#DEFFF8, color:#378E7A
    classDef Sky stroke-width:1px, stroke-dasharray:none, stroke:#374D7C, fill:#E2EBFF, color:#374D7C
    classDef Pine stroke-width:1px, stroke-dasharray:none, stroke:#254336, fill:#27654A, color:#FFFFFF
    classDef Peach stroke-width:1px, stroke-dasharray:none, stroke:#FBB35A, fill:#FFEFDB, color:#8F632D

```

### Filtering

```mermaid
---
title: Filtering flow
---
flowchart TD
    n1["Start"] -- init session state --> n2["Load working df from session state"]
    n2 --> n3["filters changed?"]
    n3 -- yes --> n4["Dialog: update filters"]
    n3 -- no --> n5["DFE changed?"]
    n5 -- yes --> n6["change falls within filter?"]
    n4 --> n1
    n5 -- no --> n2
    n6 -- yes --> n2
    n6 -- no --> n7["Find item not in filter –&gt; upsert –&gt; remove from working df"]
    n7 --> n2

    n1@{ shape: start}
    n3@{ shape: diam}
    n5@{ shape: diam}
    n6@{ shape: diam}
```

##  Backend design

```mermaid
erDiagram
    PAYMENTS {
        UUID id PK
        STRING description
        FLOAT income
        FLOAT expense
        DATE payment_date
        BOOL checked
        UUID bank_account_id FK
        UUID expense_source_id FK
        UUID income_source_id FK
        UUID user_id FK
        TIMESTAMP _created_at
    }
    
    BANK_ACCOUNTS {
        UUID id PK
        STRING name
        FLOAT starting_balance
        UUID user_id FK
        TIMESTAMP _created_at
    }

    BANK_ACCOUNTS_VIEW {
        UUID id PK
        STRING name
        FLOAT starting_balance
        FLOAT balance
        UUID user_id FK
    }

    EXPENSE_SOURCES {
        UUID id PK
        STRING name
        FLOAT budget
        LIST(UUID) budget_tracker_ids FK
        UUID user_id FK
        TIMESTAMP _created_at
    }

    EXPENSE_SOURCES_VIEW {
        UUID id PK
        STRING name
        FLOAT budget
        FLOAT current_month
        LIST(UUID) budget_tracker_ids FK
        UUID user_id FK
    }

    INCOME_SOURCES {
        UUID id PK
        STRING name
        LIST(UUID) budget_tracker_ids FK
        UUID user_id FK
        TIMESTAMP _created_at
    }

    INCOME_SOURCES_VIEW {
        UUID id PK
        STRING name
        FLOAT current_month
        LIST(UUID) budget_tracker_ids FK
        UUID user_id FK
    }

    BUDGET_TRACKER {
        UUID id PK
        STRING name
        FLOAT total_budget
        UUID user_id FK
        TIMESTAMP _created_at
    }

    FUN_SPENDING {
        UUID id PK
        STRING name
        FLOAT cost
        FLOAT current_month
        FLOAT banked
        UUID budget_tracker_id FK
        UUID user_id FK
        TIMESTAMP _created_at
    }

    BUDGET_TRACKER_VIEW {
        UUID id PK
        STRING name
        FLOAT total_budget
        FLOAT current_month
        UUID user_id FK
    }

    USER_INFO {
        UUID user_id PK
        STRING full_name
        STRING email
        TIMESTAMP created_at
    }

    BANK_ACCOUNTS ||..o{ PAYMENTS : "attributes"
    EXPENSE_SOURCES ||--o{ PAYMENTS : "categorises"
    INCOME_SOURCES ||--o{ PAYMENTS : "categorises"
    BUDGET_TRACKER }o--o{ EXPENSE_SOURCES : "categorises"
    BUDGET_TRACKER }o--o{ INCOME_SOURCES : "sums"
    BUDGET_TRACKER ||--o{ FUN_SPENDING : "splits"
    BANK_ACCOUNTS ||--|| BANK_ACCOUNTS_VIEW : "derives"
    EXPENSE_SOURCES ||--|| EXPENSE_SOURCES_VIEW : "derives"
    INCOME_SOURCES ||--|| INCOME_SOURCES_VIEW : "derives"
    BUDGET_TRACKER ||--|| BUDGET_TRACKER_VIEW : "derives"

```

### Example expense sources view

```SQL
CREATE OR REPLACE VIEW EXPENSE_SOURCES_VIEW AS
SELECT
    es.id,
    es.name,
    es.budget,
    COALESCE(SUM(p.income - p.expense), 0) AS current_month,
    es.budget_tracker_ids,
    es._created_at
FROM
    EXPENSE_SOURCES es
LEFT JOIN
    PAYMENTS p
ON
    es.id = p.expense_source_id
WHERE
    p.payment_date BETWEEN $1 AND $2
GROUP BY
    es.id, es.name, es.budget, es.budget_tracker_ids, es._created_at;
```

### Budget Tracker view

```SQL
CREATE OR REPLACE VIEW BUDGET_TRACKER_VIEW AS
SELECT
    bt.id,
    bt.name,
    bt.total_budget,
    bt._created_at,
    COALESCE(SUM(esv.current_month), 0) AS current_month
FROM
    BUDGET_TRACKER bt
LEFT JOIN
    EXPENSE_SOURCES es ON bt.id = ANY(es.budget_tracker_ids)
LEFT JOIN
    EXPENSE_SOURCES_VIEW esv ON es.id = esv.id
LEFT JOIN
    INCOME_SOURCES is ON bt.id = ANY(is.budget_tracker_ids)
LEFT JOIN
    INCOME_SOURCES_VIEW isv ON is.id = isv.id
GROUP BY
    bt.id, bt.name, bt.total_budget, bt._created_at;
```

### Payments example

```SQL
CREATE TABLE PAYMENTS (
    id UUID PRIMARY KEY,
    description TEXT,
    income FLOAT,
    expense FLOAT,
    payment_date DATE,
    checked BOOLEAN,
    bank_account_id UUID REFERENCES BANK_ACCOUNTS(id),
    expense_source_id UUID REFERENCES EXPENSE_SOURCES(id),
    income_source_id UUID REFERENCES INCOME_SOURCES(id),
    user_id UUID REFERENCES USER_INFO(user_id),
    _created_at TIMESTAMP
)
```

###
