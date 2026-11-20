-- Cloud costs in EUR (USD bills converted at the ECB monthly average of the service month) with an allocation rule.
-- Allocation: 1) product tag; 2) rule for untagged AI resources (AI service category or "agents" resources) -> ai;
-- 3) staging -> non-production (R&D, not COGS); 4) anything else -> unallocated, spread on ARR in the unit economics.
create or replace table int_cloud_costs_eur as
select f.*, x.usd_per_eur,
       case when f.billing_currency = 'USD' then f.billed_cost / x.usd_per_eur else f.billed_cost end as cost_eur,
       case when f.billing_currency = 'USD' then f.list_cost / x.usd_per_eur else f.list_cost end as list_cost_eur,
       case f.provider when 'AWS' then 'AWS-Paris' when 'Microsoft' then 'Azure-FR' else 'OVH-FR' end as hosting_region,
       json_extract_string(f.tags, '$.product') as tag_product,
       json_extract_string(f.tags, '$.component') as tag_component,
       json_extract_string(f.tags, '$.env') as tag_env,
       f.tags = '{}' as is_untagged,
       coalesce(json_extract_string(f.tags, '$.env'), 'prod') <> 'staging' as is_production,
       case when json_extract_string(f.tags, '$.product') is not null then json_extract_string(f.tags, '$.product')
            when json_extract_string(f.tags, '$.env') = 'staging' then 'non-production'
            when f.service_category = 'AI and Machine Learning' or f.resource_id like '%agents%' then 'ai'
            else 'unallocated' end as product_allocated,
       case when json_extract_string(f.tags, '$.product') is not null then 'tag'
            when json_extract_string(f.tags, '$.env') = 'staging' then 'tag (env)'
            when f.service_category = 'AI and Machine Learning' or f.resource_id like '%agents%' then 'rule: AI service or agents resource'
            else 'none' end as allocation_method
from stg_cloud_costs_focus f
join int_fx_monthly x using (month);
