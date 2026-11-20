-- CRM export (HubSpot-like, SIMULATED). Owner: RevOps Manager. Grain: one row per company / per deal.
create or replace view stg_crm_companies as
select crm_company_id, trim(company_name) as company_name, domain, segment, country, lifecycle_stage
from read_csv_auto('data/sim/crm_companies.csv', header = true);

create or replace view stg_crm_deals as
select deal_id, crm_company_id, deal_name, deal_type, pipeline_stage,
       cast(close_date as date) as close_date, cast(amount_eur as double) as amount_eur,
       cast(contract_term_months as integer) as contract_term_months,
       cast(contract_start_date as date) as contract_start_date, owner_team
from read_csv_auto('data/sim/crm_deals.csv', header = true);
