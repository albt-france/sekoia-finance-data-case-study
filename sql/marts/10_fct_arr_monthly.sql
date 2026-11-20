-- ARR bridge by month: opening, new, expansion, contraction, churn, closing.
-- Two bases side by side: the reference (contracts, clean) and the naive query on the raw billing export.
create or replace table fct_arr_monthly as
with b as (
    select 'contracts (clean)' as basis, month, customer_key as k, arr_eur from int_arr_customer_month
    union all
    select 'billing raw (by account)', month, billing_account_id, arr_eur from int_arr_account_month_raw
), keys as (
    select distinct basis, k from b
), g as (
    select m.month, keys.basis, keys.k, coalesce(b.arr_eur, 0) as arr
    from int_months m
    cross join keys
    left join b on b.basis = keys.basis and b.k = keys.k and b.month = m.month
), l as (
    select *, lag(arr) over (partition by basis, k order by month) as prev from g
)
select month, basis,
       count(*) filter (where arr > 0) as customers,
       sum(prev) as arr_open,
       sum(case when prev = 0 and arr > 0 then arr else 0 end) as new_arr,
       sum(case when prev > 0 and arr > prev then arr - prev else 0 end) as expansion_arr,
       -sum(case when prev > 0 and arr > 0 and arr < prev then prev - arr else 0 end) as contraction_arr,
       -sum(case when prev > 0 and arr = 0 then prev else 0 end) as churned_arr,
       sum(arr) as arr_close,
       count(*) filter (where prev = 0 and arr > 0) as new_logos,
       count(*) filter (where prev > 0 and arr = 0) as churned_logos
from l
where prev is not null
group by month, basis
order by basis, month;
