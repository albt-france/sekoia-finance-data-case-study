-- Trailing 12-month NRR and GRR, for all customers and by cohort (year of first contract).
-- NRR = ARR today of the customers who had ARR 12 months ago / their ARR 12 months ago (new customers excluded).
-- GRR = same, each customer capped at its ARR 12 months ago (expansion excluded).
create or replace table fct_nrr_cohort as
with a as (
    select month, customer_key as k, arr_eur from int_arr_customer_month
), pairs as (
    select m.month, b.k, b.arr_eur as base, coalesce(n.arr_eur, 0) as now_
    from int_months m
    join a b on b.month = cast(m.month - interval 12 month as date)
    left join a n on n.k = b.k and n.month = m.month
    where m.month >= date '2025-12-01'
), r as (
    select month, billing_account_id as k, arr_eur from int_arr_account_month_raw
), pairs_raw as (
    select m.month, b.k, b.arr_eur as base, coalesce(n.arr_eur, 0) as now_
    from int_months m
    join r b on b.month = cast(m.month - interval 12 month as date)
    left join r n on n.k = b.k and n.month = m.month
    where m.month >= date '2025-12-01'
)
select month, 'All' as cohort, 'contracts (clean)' as basis, count(*) as customers_base, sum(base) as arr_base, sum(now_) as arr_now,
       sum(now_) / sum(base) as nrr, sum(least(now_, base)) / sum(base) as grr
from pairs group by month
union all
select p.month, c.cohort, 'contracts (clean)', count(*), sum(base), sum(now_), sum(now_) / sum(base), sum(least(now_, base)) / sum(base)
from pairs p join int_customer_cohort c on c.customer_key = p.k
group by p.month, c.cohort
union all
select month, 'All', 'billing raw (by account)', count(*), sum(base), sum(now_), sum(now_) / sum(base), sum(least(now_, base)) / sum(base)
from pairs_raw group by month
order by basis, cohort, month;
