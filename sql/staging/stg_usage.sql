-- Product usage export (platform, SIMULATED). Owner: Data Engineering. Keyed by CRM company id.
create or replace view stg_customer_usage as
select cast(month || '-01' as date) as month, crm_company_id, tenant_id, cast(avg_ingest_gb_day as double) as avg_ingest_gb_day,
       cast(retention_days as integer) as retention_days, cast(stored_gb as double) as stored_gb, hosting_region,
       cast(ai_queries as bigint) as ai_queries
from read_csv_auto('data/sim/customer_usage.csv', header = true, types = {'month': 'VARCHAR'});
