-- Budget 2026 (frozen Dec 2025) against the ledger, by month and budget line, January to November 2026.
-- Payroll lines use the department analytic code; central accruals (bonus, paid leave) are kept out and reconciled separately.
create or replace table fct_budget_vs_actual as
with b as (
    select * from stg_budget_2026 where month <= date '2026-11-01'
), a as (
    select month, account, analytic_code, sum(net_debit_eur) as net_debit_eur from int_gl_account_month group by all
)
select b.month, b.line_group, b.budget_line, b.gl_account, b.department, b.budget_eur,
       case when b.line_group = 'Revenue' then -(select coalesce(sum(net_debit_eur), 0) from a where a.month = b.month and a.account = b.gl_account)
            when b.line_group = 'Payroll' then (select coalesce(sum(net_debit_eur), 0) from a
                                                where a.month = b.month and a.account in ('641000', '645000') and a.analytic_code = b.department)
            else (select coalesce(sum(net_debit_eur), 0) from a where a.month = b.month and a.account = b.gl_account) end as actual_eur
from b;

alter table fct_budget_vs_actual add column variance_eur double;
alter table fct_budget_vs_actual add column variance_pct double;
alter table fct_budget_vs_actual add column favorable boolean;
update fct_budget_vs_actual set variance_eur = actual_eur - budget_eur,
       variance_pct = (actual_eur - budget_eur) / nullif(budget_eur, 0),
       favorable = case when line_group = 'Revenue' then actual_eur >= budget_eur else actual_eur <= budget_eur end;
