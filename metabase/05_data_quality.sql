-- Tab 5 - Data quality. Shows whether the numbers of the other tabs are publishable.

-- Q5.1 Reconciliation status grid (pivot: check x month, value = status)
select check_name, strftime(month, '%Y-%m') as month, status, round(diff) as diff, round(residual) as residual, explanation
from fct_reconciliations
order by check_name, month;

-- Q5.2 Latest month: one line per check (table)
select check_name, source_a, source_b, round(value_a) as value_a, round(value_b) as value_b, round(diff) as diff,
       round(diff_pct * 100, 2) as diff_pct, status, explanation
from fct_reconciliations
where month = (select max(month) from fct_reconciliations)
order by check_name;

-- Q5.3 CRM -> billing ARR cascade (waterfall)
select strftime(month, '%Y-%m') as month, step_order, step, round(amount_eur) as amount_eur
from fct_arr_waterfall
order by month, step_order;

-- Q5.4 Test results of the last build (table; data/marts/test_results.csv loaded as table test_results)
select test, status, failing_rows from test_results order by status desc, test;
