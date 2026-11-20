-- CRM closed-won deals matched to billing contract lines (the billing line stores the CRM deal id).
-- Each gap between CRM and billing is classified by rule:
--   tcv_effect      multi-year deal typed at total contract value: amount / (term / 12) is the annual value
--   discount_effect annualised CRM amount above the billed value (last discount never typed back into the CRM)
--   orphan_effect   closed-won deal with no billing contract (handover gap)
create or replace table int_crm_deal_lines as
with d as (
    select *, cast(contract_start_date + to_months(contract_term_months) - interval 1 day as date) as crm_end_date
    from stg_crm_deals
    where pipeline_stage = 'Closed won'
)
select d.deal_id, d.crm_company_id, d.deal_type, d.amount_eur as crm_amount_eur, d.contract_term_months,
       d.contract_start_date, d.crm_end_date, k.contract_id, k.customer_key, k.annual_value_eur as billing_acv_eur,
       k.start_date as billing_start, k.end_date_clean as billing_end,
       case when d.contract_term_months > 12 and d.deal_type <> 'Upsell'
            then d.amount_eur / (d.contract_term_months / 12.0) else d.amount_eur end as crm_annualized_eur
from d
left join int_contracts_clean k on k.crm_deal_id = d.deal_id;

create or replace table int_crm_arr_month as
with x as (
    select m.month, l.*
    from int_months m
    join int_crm_deal_lines l on l.contract_start_date <= m.month_end and l.crm_end_date >= m.month_end
)
select month,
       sum(crm_amount_eur) as crm_arr_raw,
       sum(crm_amount_eur - crm_annualized_eur) as tcv_effect,
       sum(case when contract_id is not null then crm_annualized_eur - billing_acv_eur else 0 end) as discount_effect,
       sum(case when contract_id is null then crm_annualized_eur else 0 end) as orphan_effect,
       count(distinct crm_company_id) as crm_customers,
       count(*) filter (where contract_id is null) as orphan_deals
from x
group by month;
