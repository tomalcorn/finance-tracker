# finance-tracker

This app helps manage your personal finances!

## Management flow

```mermaid
flowchart TB
    bank_accounts["Bank Accounts"] --> payments
    payments --> budget_tracker
    bank_accounts --> budget_tracker
    subgraph budget_tracker["Budget Tracker"]
        expenses
        longer_term_spending["Longer Term Spending"]
    end

```
