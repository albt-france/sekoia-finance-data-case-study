-- Tab 3 - Headcount & payroll. AGGREGATED ONLY; payroll blanked for groups under 5 people. Restricted collection.

-- Q3.1 Headcount under three definitions (line)
select strftime(month, '%Y-%m') as month, hris_active_records, headcount_reported, fte_reported, paid_persons, interns, apprentices, suspected_leavers
from fct_headcount_payroll
where department = 'All departments'
order by month;

-- Q3.2 Payroll cost by department, latest month (bar)
select department, headcount_reported, fte_reported, payroll_cost_eur, payroll_cost_per_fte_eur
from fct_headcount_payroll
where department <> 'All departments' and not suppressed_small_group
  and month = (select max(month) from fct_headcount_payroll)
order by payroll_cost_eur desc;

-- Q3.3 Headcount vs budget by department, 2026 (table)
select strftime(b.month, '%Y-%m') as month, b.department, b.headcount as budget_headcount, h.headcount_reported
from stg_budget_2026 b
join fct_headcount_payroll h on h.month = b.month and h.department = b.department
where b.line_group = 'Payroll'
order by b.month, b.department;
