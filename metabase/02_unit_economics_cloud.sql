-- Tab 2 - Unit economics & cloud costs. SIMULATED usage x REAL public unit prices.

-- Q2.1 Gross margin by month (line) and COGS mix (stacked bar)
select strftime(month, '%Y-%m') as month, revenue_eur, hosting_eur, ai_inference_eur, support_payroll_eur, production_tools_eur,
       round(gross_margin_pct * 100, 1) as gross_margin_pct, round(cloud_pct_revenue * 100, 1) as cloud_pct_revenue
from fct_gross_margin
order by month;

-- Q2.2 Cloud cost by allocated product, untagged share (stacked bar)
select strftime(month, '%Y-%m') as month, product_allocated, allocation_method, round(sum(cost_eur)) as cost_eur
from int_cloud_costs_eur
group by all
order by month, product_allocated;

-- Q2.3 Customers below zero gross margin, latest month (table) - filter {{segment}} optional in Metabase
select customer_key, segment, plan_type, retention_days, stored_tb, round(revenue_month_eur) as revenue_month_eur,
       round(storage_cost_eur + search_compute_cost_eur) as retention_cost_eur, round(cogs_eur) as cogs_eur,
       round(gross_margin_pct * 100, 1) as gross_margin_pct
from fct_unit_economics
where month = (select max(month) from fct_unit_economics)
order by gross_margin_pct
limit 20;

-- Q2.4 AWS bill: price / volume / FX (waterfall)
select comparison, strftime(month, '%Y-%m') as month, round(base_eur) as base_eur, round(volume_effect_eur) as volume,
       round(price_effect_eur) as price, round(fx_effect_eur) as fx, round(actual_eur) as actual_eur
from fct_cloud_price_volume_fx
order by comparison, month;
