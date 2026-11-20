-- AWS bill in EUR = list cost in USD (volume) x (1 - discount) (price) / USD per EUR (FX).
-- volume = (L1 - L0) x (1 - d0) / r0 ; price = L1 x (d0 - d1) / r0 ; fx = L1 x (1 - d1) x (1/r1 - 1/r0) ; the three add up exactly.
-- Two comparisons: each 2026 month against budget, and the last three months against the three before.
create or replace table fct_cloud_price_volume_fx as
with aws as (
    select month, sum(list_cost) as list_usd, sum(billed_cost) as billed_usd, sum(cost_eur) as eur
    from int_cloud_costs_eur where provider = 'AWS' group by month
), vs_budget as (
    select a.month, 'actual vs budget' as comparison,
           b.aws_list_cost_usd as l0, b.aws_discount_rate as d0, b.usd_per_eur as r0, b.budget_eur as eur0,
           a.list_usd as l1, 1 - a.billed_usd / a.list_usd as d1, a.billed_usd / a.eur as r1, a.eur as eur1
    from aws a join stg_budget_2026 b on b.month = a.month and b.budget_line = 'Cloud hosting - AWS'
), periods as (
    select case when month between date '2026-06-01' and date '2026-08-01' then 0 else 1 end as p,
           sum(list_usd) as l, 1 - sum(billed_usd) / sum(list_usd) as d, sum(billed_usd) / sum(eur) as r, sum(eur) as eur
    from aws where month between date '2026-06-01' and date '2026-11-01' group by 1
), vs_prev as (
    select date '2026-11-01' as month, 'Sep-Nov 2026 vs Jun-Aug 2026' as comparison,
           p0.l as l0, p0.d as d0, p0.r as r0, p0.eur as eur0, p1.l as l1, p1.d as d1, p1.r as r1, p1.eur as eur1
    from periods p0, periods p1 where p0.p = 0 and p1.p = 1
), x as (
    select * from vs_budget union all select * from vs_prev
)
select month, comparison, eur0 as base_eur, eur1 as actual_eur, eur1 - eur0 as change_eur,
       (l1 - l0) * (1 - d0) / r0 as volume_effect_eur,
       l1 * (d0 - d1) / r0 as price_effect_eur,
       l1 * (1 - d1) * (1 / r1 - 1 / r0) as fx_effect_eur,
       l0 as base_list_usd, l1 as actual_list_usd, d0 as base_discount, d1 as actual_discount, r0 as base_usd_per_eur, r1 as actual_usd_per_eur
from x
order by comparison, month;
