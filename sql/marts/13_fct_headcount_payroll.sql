-- Headcount under three definitions + payroll cost. AGGREGATED ONLY (company and department level).
-- Confidentiality rule: payroll figures are blanked for any group of fewer than 5 people.
--   hris_active_records : every active HRIS record at month end (interns and stale records included)
--   headcount_reported  : employment contracts active at month end (CDI, CDD, apprentices), interns and suspected leavers excluded
--   paid_persons        : distinct people with a payslip in the month (interns' stipend and leavers' final settlement included)
create or replace table fct_headcount_payroll as
with e as (
    select * from int_employee_month
), agg as (
    select month, 'All departments' as department,
           count(*) filter (where hris_active_month_end) as hris_active_records,
           count(*) filter (where hris_active_month_end and contract_type <> 'Intern' and not suspected_leaver) as headcount_reported,
           sum(fte) filter (where hris_active_month_end and contract_type <> 'Intern' and not suspected_leaver) as fte_reported,
           count(*) filter (where hris_active_month_end and contract_type = 'Intern') as interns,
           count(*) filter (where hris_active_month_end and contract_type = 'Apprentice' and not suspected_leaver) as apprentices,
           count(*) filter (where has_regular_payslip or has_final_settlement) as paid_persons,
           count(*) filter (where has_final_settlement) as final_settlements,
           count(*) filter (where suspected_leaver) as suspected_leavers,
           sum(payroll_cost_eur) as payroll_cost_eur
    from e group by month
    union all
    select month, department,
           count(*) filter (where hris_active_month_end),
           count(*) filter (where hris_active_month_end and contract_type <> 'Intern' and not suspected_leaver),
           sum(fte) filter (where hris_active_month_end and contract_type <> 'Intern' and not suspected_leaver),
           null, null,
           count(*) filter (where has_regular_payslip or has_final_settlement),
           null, null,
           sum(payroll_cost_eur)
    from e group by month, department
)
select month, department, hris_active_records, headcount_reported, round(fte_reported, 1) as fte_reported, interns, apprentices,
       paid_persons, final_settlements, suspected_leavers,
       case when paid_persons >= 5 then round(payroll_cost_eur, 0) end as payroll_cost_eur,
       case when paid_persons >= 5 and fte_reported > 0 then round(payroll_cost_eur / fte_reported, 0) end as payroll_cost_per_fte_eur,
       paid_persons < 5 as suppressed_small_group
from agg
order by month, department = 'All departments' desc, department;
