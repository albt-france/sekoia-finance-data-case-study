-- Billing export (Younium-like, SIMULATED). Owner: Head of Finance (billing ops). Grain: account / contract line / invoice.
create or replace view stg_billing_accounts as
select billing_account_id, trim(account_name) as account_name, upper(replace(vat_number, ' ', '')) as vat_number,
       country, crm_company_id, created_in
from read_csv_auto('data/sim/billing_accounts.csv', header = true, all_varchar = true);

create or replace view stg_billing_contracts as
select contract_id, billing_account_id, crm_deal_id, product,
       cast(start_date as date) as start_date, cast(end_date as date) as end_date,
       cast(term_months as integer) as term_months, cast(annual_value_eur as double) as annual_value_eur,
       billing_frequency, plan_type, cast(committed_ingest_gb_day as double) as committed_ingest_gb_day,
       cast(retention_days as integer) as retention_days, line_type, source_system
from read_csv_auto('data/sim/billing_contracts.csv', header = true);

create or replace view stg_billing_invoices as
select invoice_id, billing_account_id, contract_id, cast(invoice_date as date) as invoice_date,
       cast(service_period_start as date) as service_period_start, cast(service_period_end as date) as service_period_end,
       invoice_type, cast(amount_excl_tax_eur as double) as amount_excl_tax_eur, cast(vat_eur as double) as vat_eur,
       currency, cast(due_date as date) as due_date, cast(paid_date as date) as paid_date
from read_csv_auto('data/sim/billing_invoices.csv', header = true);
