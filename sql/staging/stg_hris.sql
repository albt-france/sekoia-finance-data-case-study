-- HRIS export (Lucca-like, SIMULATED). Owner: People team. Confidential: never exposed below department level.
create or replace view stg_hris_employees as
select employee_id, department, job_level, contract_type, cast(start_date as date) as start_date,
       cast(end_date as date) as end_date, cast(fte as double) as fte, cast(annual_gross_eur as double) as annual_gross_eur,
       work_location, status
from read_csv_auto('data/sim/hris_employees.csv', header = true);
