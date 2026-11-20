-- Recruiting export (TeamTailor-like, SIMULATED). Owner: People team.
create or replace view stg_ats_requisitions as
select requisition_id, department, job_level, cast(opened_date as date) as opened_date, status,
       cast(hired_date as date) as hired_date, cast(start_date as date) as start_date, source, cast(budgeted as boolean) as budgeted
from read_csv_auto('data/sim/ats_requisitions.csv', header = true);
