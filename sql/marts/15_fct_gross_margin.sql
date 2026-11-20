-- Company gross margin by month. COGS = production hosting + AI inference + support & SOC operations payroll + production tools.
-- Cloud costs are taken in the month of service (FOCUS ChargePeriodStart), not the month the bill was booked.
-- Non-production cloud (staging) is R&D, not COGS. Public benchmarks: latest 10-K of four listed security vendors.
create or replace table fct_gross_margin as
with rev as (
    select month, -sum(net_debit_eur) filter (where account in ('706000', '709000')) as saas_revenue_eur,
           -sum(net_debit_eur) filter (where account = '706100') as services_revenue_eur
    from int_gl_account_month group by month
), cloud as (
    select month,
           sum(cost_eur) filter (where is_production and product_allocated <> 'ai') as hosting_eur,
           coalesce(sum(cost_eur) filter (where product_allocated = 'ai'), 0) as ai_inference_eur,
           sum(cost_eur) filter (where not is_production) as non_production_cloud_eur,
           coalesce(sum(cost_eur) filter (where is_untagged), 0) as untagged_cloud_eur,
           sum(cost_eur) as cloud_total_eur
    from int_cloud_costs_eur group by month
), pay as (
    select month, sum(net_debit_eur) as support_payroll_eur from int_gl_account_month
    where account in ('641000', '645000') and analytic_code = 'SOC Operations & Support' group by month
), tools as (
    select month, sum(net_debit_eur) as production_tools_eur from int_gl_account_month where account = '604500' group by month
)
select m.month, saas_revenue_eur, services_revenue_eur, saas_revenue_eur + services_revenue_eur as revenue_eur,
       hosting_eur, ai_inference_eur, support_payroll_eur, production_tools_eur,
       hosting_eur + ai_inference_eur + support_payroll_eur + production_tools_eur as cogs_eur,
       1 - (hosting_eur + ai_inference_eur + support_payroll_eur + production_tools_eur) / (saas_revenue_eur + services_revenue_eur) as gross_margin_pct,
       (hosting_eur + ai_inference_eur) / (saas_revenue_eur + services_revenue_eur) as cloud_pct_revenue,
       non_production_cloud_eur, untagged_cloud_eur, cloud_total_eur
from int_months m
join rev using (month) join cloud using (month) join pay using (month) join tools using (month)
order by m.month;

create or replace table fct_public_benchmarks as
select company, period_end, revenue as revenue_usd, gross_margin, rnd_pct_revenue, sm_pct_revenue, deferred_rev_pct_revenue,
       'SEC EDGAR XBRL company facts, form 10-K' as source
from stg_sec_benchmarks
order by company, period_end;
