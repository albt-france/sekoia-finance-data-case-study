-- Gross margin per customer and month. Revenue = contracted ARR / 12. COGS pools and their allocation drivers:
--   storage (per hosting region)       -> stored GB          search compute (AWS)  -> stored GB
--   ingest compute (AWS, Azure region) -> GB ingested / day  sovereign compute (OVH) -> GB ingested / day
--   ai inference (tag or rule)         -> AI queries         shared platform, untagged non-AI -> ARR
--   support & SOC operations payroll   -> segment weight     production tools (604500) -> ARR
create or replace table int_cogs_pools as
with c as (
    select * from int_cloud_costs_eur where is_production
)
select month, 'storage' as pool, hosting_region as region_set, 'stored_gb' as driver, sum(cost_eur) as amount_eur
from c where service_category = 'Storage' and tag_product = 'siem' group by month, hosting_region
union all
select month, 'search compute', 'AWS-Paris', 'stored_gb', sum(cost_eur) from c where tag_component = 'search' group by month
union all
select month, 'ingest compute', 'AWS-Paris,Azure-FR', 'ingest', sum(cost_eur) from c where tag_component = 'ingest' group by month
union all
select month, 'sovereign compute', 'OVH-FR', 'ingest', sum(cost_eur) from c
where provider = 'OVHcloud' and service_category = 'Compute' and tag_product = 'siem' group by month
union all
select month, 'ai inference', 'ALL', 'ai_queries', sum(cost_eur) from c where product_allocated = 'ai' group by month
union all
select month, 'shared platform', 'ALL', 'arr', sum(cost_eur) from c
where product_allocated in ('soar', 'cti', 'platform', 'unallocated') group by month
union all
select month, 'support & SOC operations payroll', 'ALL', 'segment_weight', sum(net_debit_eur) from int_gl_account_month
where account in ('641000', '645000') and analytic_code = 'SOC Operations & Support' group by month
union all
select month, 'production tools', 'ALL', 'arr', sum(net_debit_eur) from int_gl_account_month where account = '604500' group by month;

create or replace table fct_unit_economics as
with u as (
    select u.month, x.customer_key, x.segment, u.hosting_region, u.avg_ingest_gb_day, u.stored_gb, u.retention_days, u.ai_queries,
           coalesce(a.arr_eur, 0) as arr_eur,
           case x.segment when 'SMB' then 1 when 'Mid-market' then 2 else 4 end as segment_weight
    from stg_customer_usage u
    join int_customer_master x on x.crm_company_id = u.crm_company_id
    left join int_arr_customer_month a on a.month = u.month and a.customer_key = x.customer_key
), d as (
    select p.month, p.pool, p.region_set, p.amount_eur, u.customer_key,
           case p.driver when 'stored_gb' then u.stored_gb when 'ingest' then u.avg_ingest_gb_day when 'ai_queries' then u.ai_queries
                         when 'arr' then u.arr_eur else u.segment_weight end as drv
    from int_cogs_pools p
    join u on u.month = p.month and (p.region_set = 'ALL' or contains(p.region_set, u.hosting_region))
), alloc as (
    select month, customer_key, pool, amount_eur * drv / nullif(sum(drv) over (partition by month, pool, region_set), 0) as cost_eur
    from d
), piv as (
    select month, customer_key,
           sum(cost_eur) filter (where pool = 'storage') as storage_cost_eur,
           sum(cost_eur) filter (where pool = 'search compute') as search_compute_cost_eur,
           sum(cost_eur) filter (where pool in ('ingest compute', 'sovereign compute')) as ingest_compute_cost_eur,
           sum(cost_eur) filter (where pool = 'ai inference') as ai_cost_eur,
           sum(cost_eur) filter (where pool = 'shared platform') as shared_platform_cost_eur,
           sum(cost_eur) filter (where pool = 'support & SOC operations payroll') as support_cost_eur,
           sum(cost_eur) filter (where pool = 'production tools') as tools_cost_eur
    from alloc group by month, customer_key
), plan as (
    select customer_key, arg_max(plan_type, start_date) as plan_type from int_contracts_clean group by customer_key
)
select u.month, u.customer_key, u.segment, p2.plan_type, u.hosting_region, u.retention_days,
       round(u.avg_ingest_gb_day, 1) as avg_ingest_gb_day, round(u.stored_gb / 1000, 1) as stored_tb, u.ai_queries,
       u.arr_eur, u.arr_eur / 12 as revenue_month_eur,
       coalesce(storage_cost_eur, 0) as storage_cost_eur, coalesce(search_compute_cost_eur, 0) as search_compute_cost_eur,
       coalesce(ingest_compute_cost_eur, 0) as ingest_compute_cost_eur, coalesce(ai_cost_eur, 0) as ai_cost_eur,
       coalesce(shared_platform_cost_eur, 0) as shared_platform_cost_eur, coalesce(support_cost_eur, 0) as support_cost_eur,
       coalesce(tools_cost_eur, 0) as tools_cost_eur,
       coalesce(storage_cost_eur, 0) + coalesce(search_compute_cost_eur, 0) + coalesce(ingest_compute_cost_eur, 0) + coalesce(ai_cost_eur, 0)
         + coalesce(shared_platform_cost_eur, 0) + coalesce(support_cost_eur, 0) + coalesce(tools_cost_eur, 0) as cogs_eur
from u
join piv using (month, customer_key)
left join plan p2 using (customer_key);

alter table fct_unit_economics add column gross_margin_eur double;
alter table fct_unit_economics add column gross_margin_pct double;
update fct_unit_economics set gross_margin_eur = revenue_month_eur - cogs_eur,
       gross_margin_pct = case when revenue_month_eur > 0 then (revenue_month_eur - cogs_eur) / revenue_month_eur end;
