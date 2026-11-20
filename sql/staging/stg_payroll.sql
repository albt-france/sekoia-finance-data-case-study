-- Payroll register (SILAE-like, SIMULATED). Owner: People team / payroll provider. Confidential: aggregates only.
create or replace view stg_payroll_monthly as
select cast(pay_month || '-01' as date) as month, employee_id, payslip_type,
       cast(gross_eur as double) as gross_eur, cast(employer_contrib_eur as double) as employer_contrib_eur,
       cast(gross_eur as double) + cast(employer_contrib_eur as double) as payroll_cost_eur
from read_csv_auto('data/sim/payroll_monthly.csv', header = true, types = {'pay_month': 'VARCHAR'});
