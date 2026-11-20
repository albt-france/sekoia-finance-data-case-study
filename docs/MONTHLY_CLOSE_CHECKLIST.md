# Monthly close checklist (D+1 to D+5 working days)

> Working days exclude weekends and French public holidays (Nager.Date; `int_close_calendar`). Example: the April 2026 close
> runs from Monday 4 May (D+1) to Monday 11 May (D+5), because 8 May is a public holiday. Roles, not names.

| Day | Step | Control (pass condition) | Prepared by | Validated by |
|---|---|---|---|---|
| D+1 | Load all exports (CRM, billing, bank, payroll, expenses, FOCUS cloud costs) | row counts vs last month within +/-20%; `run_tests.py` uniqueness and null tests OK | Finance Data Analyst | - |
| D+1 | Cloud accrual from FOCUS exports (service month), USD at ECB monthly average | FOCUS vs ledger hosting within 0.5% (or accrual booked) | Finance Data Analyst | FinOps Manager |
| D+2 | Billing: invoices of the month issued, credit notes approved | billing vs ledger subscription revenue within 0.5% | billing ops | Head of Finance |
| D+2 | CRM vs billing: deals closed-won in the month have a contract line | residual after classified differences < 1%; list of deals without contract sent | Finance Data Analyst | RevOps Manager |
| D+2 | Expenses: reports approved; known events accrued (e.g. offsite at month end) | travel variance explained or accrued | Finance Data Analyst | Head of Finance |
| D+3 | Payroll: register received; HRIS movements of the month | payroll vs ledger within 0.5%; HRIS vs payroll headcount difference = 0 or listed | People team | Head of Finance |
| D+3 | Accruals: bonus, paid leave, unbilled services | each accrual has a document and a reversal date | Head of Finance | - |
| D+4 | Bank reconciliation | bank vs ledger difference = 0 (WARN under 0.01% only with a booked fix next day) | Finance Data Analyst | Head of Finance |
| D+4 | ARR, NRR, GRR, headcount, gross margin computed from marts | test suite 100% OK; ARR change vs last month explained by the bridge | Finance Data Analyst | Head of Finance |
| D+5 | Budget vs actual with comments; price / volume / FX for cloud | every variance > 10% and > €10k has a comment | Finance Data Analyst | Head of Finance |
| D+5 | Publish Metabase dashboards and the monthly pack | dashboard date = close date; open items listed | Finance Data Analyst | Head of Finance |
