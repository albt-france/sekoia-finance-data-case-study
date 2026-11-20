# Metabase: "Finance data - monthly" dashboard

Native SQL questions ready to paste into Metabase (SQL editor), one file per dashboard tab. They read the marts built by
`python src/run_sql.py` (tables `fct_*`), so they work on any warehouse that holds those tables (DuckDB here; standard SQL,
no DuckDB-only function except `strftime`, replace by `to_char(month, 'YYYY-MM')` on PostgreSQL).
Not installed or tested in a Metabase instance: the queries were run on DuckDB.

## Dashboard layout (5 tabs)

| Tab | File | Questions (visualisation) | Filters |
|---|---|---|---|
| ARR & NRR | `01_arr_nrr.sql` | ARR bridge by month (stacked bar); ARR clean vs raw (line); NRR / GRR trailing 12 months (line); NRR by cohort (table) | month range, basis |
| Unit economics & cloud costs | `02_unit_economics_cloud.sql` | gross margin by month (line); cloud cost by product with untagged share (stacked bar); customers below zero margin (table); AWS price / volume / FX (waterfall) | month, segment, plan |
| Headcount & payroll | `03_headcount_payroll.sql` | headcount under 3 definitions (line); payroll cost by department (bar, groups >= 5 only) | month |
| Budget vs actual & cash | `04_budget_cash.sql` | variance by line (table with conditional colours); travel Jan-Feb (bar); cash and operating cash flow (line) | month, line group |
| Data quality | `05_data_quality.sql` | reconciliation status grid (pivot check x month); latest test results (table); CRM -> billing cascade (waterfall) | month |

## Rules for the Metabase instance
- Payroll questions live in a restricted collection (Finance leadership); other users see headcount and FTE only.
- Every card subtitle states the reference source ("ARR = billing contracts, clean").
- The dashboard shows the date of the last load and the test status (tab 5) so readers know if the numbers are publishable.
- Metabase models: `fct_arr_monthly`, `fct_unit_economics`, `fct_budget_vs_actual` declared as models with column descriptions copied from `docs/METRIC_DEFINITIONS.md`.
