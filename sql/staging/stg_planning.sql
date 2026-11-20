-- Budget 2026 export (Pigment-like, SIMULATED), frozen in December 2025. Owner: Finance Data Analyst (Pigment data owner).
create or replace view stg_budget_2026 as
select cast(month || '-01' as date) as month, line_group, budget_line, gl_account,
       cast(budget_eur as double) as budget_eur, cast(aws_list_cost_usd as double) as aws_list_cost_usd,
       cast(aws_discount_rate as double) as aws_discount_rate, cast(usd_per_eur as double) as usd_per_eur,
       cast(headcount as integer) as headcount, department
from read_csv_auto('data/sim/budget_2026.csv', header = true, types = {'gl_account': 'VARCHAR', 'month': 'VARCHAR'});
