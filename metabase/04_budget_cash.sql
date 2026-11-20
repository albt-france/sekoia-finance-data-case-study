-- Tab 4 - Budget vs actual & cash. Budget frozen Dec 2025 (Pigment-like export). SIMULATED.

-- Q4.1 Year-to-date variance by budget line (table, conditional colour on favorable)
select line_group, budget_line, round(sum(budget_eur)) as budget_ytd, round(sum(actual_eur)) as actual_ytd,
       round(sum(variance_eur)) as variance_ytd, round(sum(variance_eur) / sum(budget_eur) * 100, 1) as variance_pct,
       case when line_group = 'Revenue' then sum(variance_eur) >= 0 else sum(variance_eur) <= 0 end as favorable
from fct_budget_vs_actual
group by line_group, budget_line
order by line_group, abs(sum(variance_eur)) desc;

-- Q4.2 Monthly variance of one line (bar) - Metabase filter {{budget_line}}, default 'Travel and expenses'
select strftime(month, '%Y-%m') as month, budget_eur, actual_eur, variance_eur
from fct_budget_vs_actual
where budget_line = 'Travel and expenses'
order by month;

-- Q4.3 Cash position and operating cash flow (line + bar)
select strftime(month, '%Y-%m') as month, round(closing_cash) as closing_cash, round(operating_cash_flow) as operating_cash_flow,
       round(operating_cf_6m_avg) as operating_cf_6m_avg, round(runway_months, 1) as runway_months, round(bank_vs_gl_diff, 2) as bank_vs_gl_diff
from fct_cash
order by month;
