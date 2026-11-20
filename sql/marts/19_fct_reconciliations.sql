-- Every reconciliation, every month: value in source A, value in source B, difference, explained part, residual, status.
-- Status: OK (difference within threshold) / EXPLAINED (residual within threshold after documented items) / WARN (cash
-- difference not zero but under the threshold) / KO (residual above threshold: investigate before publishing the number).
-- Timing rule: a difference reversed by the next or previous month within the threshold is a cut-off (explained).
create or replace table fct_reconciliations as
with crm as (
    select c.month, 'CRM vs billing ARR' as check_name, 'CRM closed-won deals (amount as typed)' as source_a, 'Billing contracts (clean)' as source_b,
           c.crm_arr_raw as value_a, b.arr as value_b, c.tcv_effect + c.discount_effect + c.orphan_effect as explained,
           0.01 as threshold_pct, 'multi-year deals typed at TCV, CRM amount before last discount, closed-won deals not in billing' as explanation
    from int_crm_arr_month c
    join (select month, sum(arr_eur) as arr from int_arr_customer_month group by month) b using (month)
), billing_rev as (
    select m.month, sum(i.amount_excl_tax_eur / (date_diff('month', i.service_period_start, i.service_period_end) + 1)) as expected
    from stg_billing_invoices i
    join int_months m on m.month between date_trunc('month', i.service_period_start) and date_trunc('month', i.service_period_end)
    where i.invoice_type = 'subscription'
    group by m.month
), rev as (
    select b.month, 'Billing vs ledger subscription revenue', 'Billing invoices spread over service period', 'Ledger 706000',
           b.expected, -g.v, 0.0, 0.005, 'cut-off: invoices recognised in the following month'
    from billing_rev b join (select month, sum(net_debit_eur) as v from int_gl_account_month where account = '706000' group by month) g using (month)
), pay as (
    select p.month, 'Payroll register vs ledger payroll cost', 'Payroll register (gross + employer contributions)', 'Ledger 641000 + 645000',
           p.v, g.v, -coalesce(g.manual, 0), 0.005, 'central accruals booked by Finance (year-end bonus accrual and its reversal)'
    from (select month, sum(payroll_cost_eur) as v from stg_payroll_monthly group by month) p
    join (select month, sum(net_debit_eur) as v, sum(net_debit_eur) filter (where journal = 'OD') as manual
          from int_gl_account_month where account in ('641000', '645000') group by month) g using (month)
), cloud as (
    select c.month, 'Cloud bills vs ledger hosting', 'FOCUS cost exports in EUR (service month)', 'Ledger 604100-604300',
           c.v, g.v, 0.0, 0.005, 'cut-off: a bill booked the month after its service month'
    from (select month, sum(cost_eur) as v from int_cloud_costs_eur group by month) c
    join (select month, sum(net_debit_eur) as v from int_gl_account_month where account in ('604100', '604200', '604300') group by month) g using (month)
), cash as (
    select month, 'Bank vs ledger cash', 'Bank export closing balance', 'Ledger 512000 closing balance',
           closing_cash, gl_512_closing, 0.0, 0.0001, 'bank line not yet booked in the ledger'
    from fct_cash
), hc as (
    select month, 'HRIS vs payroll headcount', 'HRIS active records (interns excluded)', 'People with a regular payslip, active at month end',
           count(*) filter (where hris_active_month_end and contract_type <> 'Intern'),
           count(*) filter (where hris_active_month_end and contract_type <> 'Intern' and has_regular_payslip),
           count(*) filter (where suspected_leaver and contract_type <> 'Intern'), 0.0,
           'leavers whose HRIS end date was never entered (no payslip): excluded from reported headcount'
    from int_employee_month group by month
), u as (
    select * from crm union all select * from rev union all select * from pay
    union all select * from cloud union all select * from cash union all select * from hc
), d as (
    select *, value_a - value_b as diff, abs(value_b) * threshold_pct as threshold_abs,
           lead(value_a - value_b) over (partition by check_name order by month) as next_diff,
           lag(value_a - value_b) over (partition by check_name order by month) as prev_diff
    from u
), e as (
    select *,
           case when check_name in ('Billing vs ledger subscription revenue', 'Cloud bills vs ledger hosting')
                     and abs(diff) > threshold_abs
                     and (abs(diff + coalesce(next_diff, 1e12)) <= threshold_abs or abs(diff + coalesce(prev_diff, 1e12)) <= threshold_abs)
                then diff else explained end as explained_final
    from d
)
select month, check_name, source_a, source_b, round(value_a, 2) as value_a, round(value_b, 2) as value_b, round(diff, 2) as diff,
       round(diff / nullif(abs(value_b), 0), 5) as diff_pct, round(explained_final, 2) as explained, round(diff - explained_final, 2) as residual,
       threshold_pct,
       case when abs(diff) < 0.5 then 'OK'
            when abs(diff) <= threshold_abs and check_name = 'Bank vs ledger cash' then 'WARN'
            when abs(diff) <= threshold_abs then 'OK'
            when abs(diff - explained_final) <= greatest(threshold_abs, 0.5) then 'EXPLAINED'
            else 'KO' end as status,
       case when abs(diff) < 0.5 then '' else explanation end as explanation
from e
order by check_name, month;
