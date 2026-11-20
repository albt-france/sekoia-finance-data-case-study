-- Employee x month, joining the HRIS record and the payslips of the month. Person-level: never exported.
-- suspected_leaver: active in the HRIS at month end, started before the month, but no regular payslip (HRIS end date missing).
create or replace table int_employee_month as
with p as (
    select month, employee_id,
           bool_or(payslip_type = 'regular') as has_regular_payslip,
           bool_or(payslip_type = 'final_settlement') as has_final_settlement,
           sum(payroll_cost_eur) as payroll_cost_eur
    from stg_payroll_monthly
    group by all
), g as (
    select m.month, m.month_end, e.*
    from int_months m
    cross join stg_hris_employees e
)
select g.month, g.employee_id, g.department, g.contract_type, g.fte,
       (g.start_date <= g.month_end and (g.end_date is null or g.end_date >= g.month_end)) as hris_active_month_end,
       coalesce(p.has_regular_payslip, false) as has_regular_payslip,
       coalesce(p.has_final_settlement, false) as has_final_settlement,
       coalesce(p.payroll_cost_eur, 0) as payroll_cost_eur,
       (g.start_date <= g.month_end and (g.end_date is null or g.end_date >= g.month_end))
           and g.start_date < g.month and not coalesce(p.has_regular_payslip, false) as suspected_leaver
from g
left join p on p.month = g.month and p.employee_id = g.employee_id
where (g.start_date <= g.month_end and (g.end_date is null or g.end_date >= g.month)) or p.employee_id is not null;
